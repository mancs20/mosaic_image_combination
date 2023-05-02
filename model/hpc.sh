#!/bin/bash -l
#SBATCH --time=24:00:00
#SBATCH --partition=batch
#SBATCH --nodes=4
#SBATCH --mem=0
#SBATCH --ntasks-per-node=16
#SBATCH --cpus-per-task=8
#SBATCH --qos=normal

ulimit -u 10000
module load compiler/GCC/10.2.0
module load compiler/GCCcore/10.2.0
module load lang/Python/3.8.6-GCCcore-10.2.0
module load lang/Java/16.0.1
export PATH=$PATH:$HOME/.local/bin:$HOME/bin:$HOME/deps/gecode:$HOME/deps/libminizinc/build
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/deps/gecode
source ../../automotive-network-cp/mo-mzn/hpcpy/bin/activate

cd mo
cp_timeout_sec=3600
solver="gecode"
summary="../summary_hpc.csv"
res_dir="../results"
echo "Start Loop, yeay."
mkdir -p $res_dir
tasks=64
cores=8
tasks_counter=1
for f in ../data_sets/*.dzn;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    log_file=$res_dir"/free_search_gecode_"$cp_timeout_sec"_"$data_name
    echo "Start srun...."$log_file
    srun --exclusive --cpu-bind=cores -n 1 -c $cores python3 main.py --model_mzn ../mosaic_cloud2.mzn --dzn_dir ../data_sets --solver_name gecode --cp_timeout_sec $cp_timeout_sec --summary ../summary.csv --cp_strategy "free_search" --fzn_optimisation_level 1 --cores $cores $data_name 2>&1 | tee -a "$log_file" &
    [[ $((tasks_counter % tasks)) -eq 0 ]] && wait && rm -f $summary".lock"
    let tasks_counter++
  fi
done

for f in ../data_sets/*.dzn;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    log_file=$res_dir"/greedy_gecode_"$cp_timeout_sec"_"$data_name
    echo "Start srun...."$log_file
    srun --exclusive --cpu-bind=cores -n 1 -c $cores python3 main.py --model_mzn ../mosaic_cloud3.mzn --dzn_dir ../data_sets --solver_name gecode --cp_timeout_sec $cp_timeout_sec --summary ../summary.csv --cp_strategy "greedy" --fzn_optimisation_level 1 --cores $cores $data_name 2>&1 | tee -a "$log_file" &
    [[ $((tasks_counter % tasks)) -eq 0 ]] && wait && rm -f $summary".lock"
    let tasks_counter++
  fi
done
wait
