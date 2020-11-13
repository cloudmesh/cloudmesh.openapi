import os
import sys
from cloudmesh.common.Shell import Shell
import pandas as pd
import numpy as np
from cloudmesh.common.Benchmark import Benchmark
from timeit import default_timer
from socket import gethostname
import matplotlib.pyplot as plt

def main(argv):
    Benchmark.Start()
    home = os.environ['HOME']
    script_output_dir = f"{home}/.cloudmesh/eigenfaces-svm/vm_script_output/"
    benchmark_output_dir = f"{home}/.cloudmesh/eigenfaces-svm/benchmark_output/"

    if not os.path.exists(f"{home}/.cloudmesh/eigenfaces-svm"):
        os.mkdir(f"{home}/.cloudmesh/eigenfaces-svm")
    if not os.path.exists(script_output_dir):
        os.mkdir(script_output_dir)
    if not os.path.exists(benchmark_output_dir):
        os.mkdir(benchmark_output_dir)

    # Run script to launch VMs and benchmark OpenAPI service if command line arg "run" passed
    if len(argv) > 1 and argv[1]=="run":
        clouds = ['aws', 'google', 'azure']
        runtimes_dic = {'google': [],
                    'aws': [],
                    'azure': []}
        num_trials = 3
        print(f"Running {num_trials} trials for each cloud in {clouds}")
        for cloud in clouds:
            Shell.run(f"cms set cloud={cloud}")
            for i in range(num_trials):
                vm_name = f"{cloud}-{i}"
                print(f"Creating and running test on VM {vm_name}")
                start = default_timer()
                result = Shell.run(f"{home}/cm/cloudmesh-openapi/tests/generator-eigenfaces-svm/eigenfaces-svm-full-script {vm_name} > {script_output_dir}{cloud}-{i}")
                end = default_timer()
                print(f"Script on {vm_name} finished in {end - start} seconds")
                runtimes_dic[cloud].append(end-start)
            runtimes = np.asarray(runtimes_dic[cloud])
            print (f"\n{cloud} script run time mean: {runtimes.mean()}")
            print(f"{cloud} script run time min: {runtimes.min()}")
            print(f"{cloud} script run time max: {runtimes.max()}")
            print(f"{cloud} script run time std: {runtimes.std()}\n")

    # Scarpe benchmark output from script outputs
    print(f'Scraping benchmarks from script output at {script_output_dir}')
    script_outputs = os.listdir(script_output_dir)
    for file in script_outputs:
        with open(f"{script_output_dir}{file}",'r') as f:
            b = open(f"{benchmark_output_dir}{file}-benchmark", "w")
            b.write("csv,timer,status,time,sum,start,tag,uname.node,user,uname.system,platform.version\n")
            found_benchmark = False
            for line in f.readlines():
                if line[0:10] == "# csv,test": #some shells return csv info twice once as error "info" and normal output
                    found_benchmark = True
                    b.write(line[2:]) #keep csv,...
            b.close()
            if not found_benchmark:
                print(f"Error on script {script_output_dir}{file}")
                if os.path.exists(f"{benchmark_output_dir}{file}-benchmark"):
                    os.remove(f"{benchmark_output_dir}{file}-benchmark")

    # Read benchmark output and compute statistics
    print(f'Reading benchmarks from benchmark output at {benchmark_output_dir}')
    columns = ["csv","timer","status","time","sum","start","tag","uname.node","user","uname.system","platform.version, cloud"]
    benchmark_df = pd.DataFrame(columns=columns)
    benchmark_outputs = os.listdir(benchmark_output_dir)
    for file in benchmark_outputs:
        cloud = file.split("-")[0]
        df = pd.read_csv(f"{benchmark_output_dir}{file}")
        df['cloud'] = cloud
        if cloud == 'aws':
            df.loc[df['uname.node'].str.startswith("ip"),["uname.node"]] = 'aws' + "-" +file.split("-")[1]
        benchmark_df = pd.concat([benchmark_df, df])

    benchmark_df['test_type'] = 'local'
    benchmark_df.loc[benchmark_df['uname.node'] == gethostname(),['test_type']] = 'remote'

    print("Printing trial statistics:")
    result = ""
    stats = {}
    stats_df = pd.DataFrame(columns=['test', 'type', 'cloud', 'mean', 'min', 'max', 'std'])
    for cloud in benchmark_df['cloud'].unique():
        result += f"{cloud} has {len(benchmark_df.loc[benchmark_df['cloud']==cloud]['uname.node'].unique())-1} VM samples.\n"
        stats[cloud] = {}
        for timer in benchmark_df['timer'].unique():
            for test_type in benchmark_df['test_type'].unique():
                stats[cloud][(timer, test_type)] = {}
                df = benchmark_df.loc[(benchmark_df['cloud'] == cloud) & (benchmark_df['timer'] == timer) & (benchmark_df['test_type'] == test_type), ['time']]
                if len(df.values) > 0:
                    mean = df.values.mean()
                    min = df.values.min()
                    max = df.values.max()
                    std = df.values.std()
                    result += f"{cloud} {timer} {test_type} samples: {len(df.values)}\n"
                    result += f"{cloud} {timer} {test_type} mean: {mean}\n"
                    result += f"{cloud} {timer} {test_type} min: {min}\n"
                    result += f"{cloud} {timer} {test_type} max: {max}\n"
                    result += f"{cloud} {timer} {test_type} std: {std}\n\n"
                    stats[cloud][(timer, test_type)]['mean'] = mean
                    stats[cloud][(timer, test_type)]['min'] = min
                    stats[cloud][(timer, test_type)]['max'] = max
                    stats[cloud][(timer, test_type)]['std'] = std
                    to_append = [timer, test_type, cloud, mean, min, max, std]
                    stats_series = pd.Series(to_append, index=stats_df.columns)
                    stats_df = stats_df.append(stats_series, ignore_index=True)

    print(result)

    # graph 1: download_data_local
    download_means = []
    download_mins = []
    download_stds = []
    download_labels = []
    for cloud in stats.keys():
        download_labels.append(cloud)
        cloud_mean = stats[cloud][('test_030_generator_eigenfaces_svm/test_download_data', 'local')]['mean']
        cloud_min = stats[cloud][('test_030_generator_eigenfaces_svm/test_download_data', 'local')]['min']
        cloud_std = stats[cloud][('test_030_generator_eigenfaces_svm/test_download_data', 'local')]['std']
        download_means.append(cloud_mean)
        download_mins.append(cloud_min)
        download_stds.append(cloud_std)

    download_df = stats_df.loc[(stats_df['test'] == 'test_030_generator_eigenfaces_svm/test_download_data')]
    download_means = download_df["mean"]
    download_mins = download_df["min"]
    download_stds = download_df["std"]
    download_labels = download_df["cloud"]

    plt.style.use('ggplot')
    x = download_labels
    x_pos = [i for i, _ in enumerate(x)]
    plt.bar(x_pos, download_means, bottom=download_mins,yerr=download_stds, color=["green",'orange','blue'])
    plt.xlabel("Cloud")
    plt.ylabel("Seconds")
    plt.title("Data Download Times")
    plt.xticks(x_pos, x)

    plt.show()

    # graph 2: scikitlearn_train vs opeanpi_scikitlearn_train
    openapi_means = []
    openapi_mins = []
    openapi_stds = []
    _labels = []
    scikit_means = []
    scikit_mins = []
    scikit_stds = []
    scikit_labels = []

    for cloud in stats.keys():
        download_labels.append(cloud)
        openapi = ('test_030_generator_eigenfaces_svm/test_train', 'local')
        scikit = ('test_030_generator_eigenfaces_svm/test_scikitlearn_train', 'local')
        openapi_mean = stats[cloud][openapi]['mean']
        openapi_min = stats[cloud][openapi]['min']
        openapi_std = stats[cloud][openapi]['std']
        openapi_means.append(openapi_mean)
        openapi_mins.append(openapi_min)
        openapi_stds.append(openapi_std)
        scikit_mean = stats[cloud][openapi]['mean']
        scikit_min = stats[cloud][openapi]['min']
        scikit_std = stats[cloud][openapi]['std']
        download_means.append(cloud_mean)
        download_mins.append(cloud_min)
        download_stds.append(cloud_std)

    plt.style.use('ggplot')
    x = stats.keys()
    x_pos = [i for i, _ in enumerate(x)]
    plt.bar(x_pos, download_means, bottom=download_mins, yerr=download_stds, color=["green", 'orange', 'blue'])
    plt.xlabel("Cloud")
    plt.ylabel("Seconds")
    plt.title("Data Download Times")
    plt.xticks(x_pos, x)

    plt.show()


    # graph 3: upload_local vs upload_remote,
    # graph 4  predict_local vs predict_remote



    Benchmark.Stop()
    Benchmark.print()
    return

if __name__ == "__main__":
    main(sys.argv)
