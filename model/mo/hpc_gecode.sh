#!/bin/bash -l
#SBATCH --time=04:00:00
#SBATCH --partition=batch
#SBATCH --nodes=3
#SBATCH --mem=0
#SBATCH --ntasks-per-node=16
#SBATCH --cpus-per-task=8
#SBATCH --qos=normal

module load compiler/GCC/10.2.0
module load compiler/GCCcore/10.2.0
module load lang/Python/3.8.6-GCCcore-10.2.0
module load lang/Java/16.0.1
export PATH=$PATH:$HOME/deps/libminizinc/build:$HOME/.local/bin:$HOME/bin:$HOME/deps/gecode
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/deps/gecode
source ~/deps/hpcpy/bin/activate

cp_strategy="free"
cp_timeout_sec=3600 # 60 seconds per experiment (just for test).
cp_solver="gecode" # change to ortools after test with choco
summary="summary_hpc.csv" # Where to store the results
mzn_models=("../mosaic_cloud2.mzn" "../mosaic_cloud3.mzn")
dzn_dir="../data_sets"
tmp_dir="../tmp_dir"

mkdir -p "$tmp_dir"

echo "Start Loop, yeay."

tasks=48
cores=8
tasks_counter=1
for f in "$dzn_dir"/*.dzn;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    for mzn_model in ${mzn_models[@]}; do
      mzn_model_name=$(basename -- "$mzn_model" .mzn)
      # Create a log file for this experiment (to debug in case anything goes wrong).
      log_file=$tmp_dir"/"$mzn_model_name"_"$cp_strategy"_"$cp_solver"_"$cores"_"$cp_timeout_sec"_"$data_name

      # Run the experiment asynchronously (notice the `&` at the end of the command).`
      if [[ $mzn_model_name == "mosaic_cloud2" ]] ; then
      	srun --exclusive --cpu-bind=cores -n 1 -c $cores python3 main.py --model_mzn "$mzn_model" --dzn_dir "$dzn_dir" --solver_name "$cp_solver" --cp_timeout_sec "$cp_timeout_sec" --summary "$summary" --cores "$cores" --cp_strategy "$cp_strategy" --fzn_optimisation_level 1 "$data_name" 2>&1 | tee -a "$log_file" &
      else
      	srun --exclusive --cpu-bind=cores -n 1 -c $cores python3 main.py --model_mzn "$mzn_model" --dzn_dir "$dzn_dir" --solver_name "$cp_solver" --cp_timeout_sec "$cp_timeout_sec" --summary "$summary" --cores "$cores" --cp_strategy "greedy" --fzn_optimisation_level 1 "$data_name" 2>&1 | tee -a "$log_file" &
      fi
      [[ $((tasks_counter % tasks)) -eq 0 ]] && wait && rm -f $summary".lock"
        let tasks_counter++
    done
  fi
done
wait
