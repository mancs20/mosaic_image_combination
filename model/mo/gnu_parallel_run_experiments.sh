#!/bin/bash -l

# $PARALLEL_SEQ is a special variable from GNU parallel. It gives the
# number of the job in the sequence.
#
# Here we print the sleep time, host name, and the date and time.
module load compiler/GCC/10.2.0
module load compiler/GCCcore/10.2.0
module load lang/Python/3.8.6-GCCcore-10.2.0
module load lang/Java/16.0.1
module load math/Gurobi
source ~/deps/hpcpy/bin/activate
echo "Task ${PARALLEL_SEQ}  started on host:$(hostname) date:$(date)"
echo "Start experiments yeay."

# modifications starts here
# Initialize variables with default values
#--minizinc_data 1 --model_mzn ../mosaic_cloud2.mzn --dzn_dir ../data_sets/ --problem_name sims --solver_name gurobi --front_strategy saugmecon --solver_timeout_sec 3600 --summary ../summary_test_sims_2_cost_cloud.csv --cores 6 --solver_search_strategy free --fzn_optimisation_level 1 paris_50
problem_name=sims
solver_name=gurobi
front_strategy=saugmecon
instance_name=paris_30

# Parse named parameters
while [[ $# -gt 0 ]]; do
  key="$1"

  case $key in
    --problem_name)
      problem_name="$2"
      shift # Shift past the argument
      shift # Shift past the value
      ;;
    --solver_name)
      solver_name="$2"
      shift # Shift past the argument
      shift # Shift past the value
      ;;
    --front_strategy)
      front_strategy="$2"
      shift # Shift past the argument
      shift # Shift past the value
      ;;
    --instance_name)
      instance_name="$2"
      shift # Shift past the argument
      shift # Shift past the value
      ;;
    *)
      # Unknown argument
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

# end modifications
echo "problem_name: $problem_name"
echo "solver_name: $solver_name"
echo "front_strategy: $front_strategy"
echo "instance_name: $instance_name"

python main.py --minizinc_data 1 --model_mzn ../mosaic_cloud2.mzn --dzn_dir ../data_sets/ --problem_name "$problem_name" --solver_name "$solver_name" --front_strategy "$front_strategy" --solver_timeout_sec 3600 --summary ../summary_sims_2obj_cost_cloud.csv --cores 8 --solver_search_strategy free --fzn_optimisation_level 1 --instance_name "$instance_name"