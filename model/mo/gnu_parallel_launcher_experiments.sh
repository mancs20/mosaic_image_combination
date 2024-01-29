#!/bin/bash -l
#SBATCH --time=01:30:00
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --ntasks-per-node=8
#SBATCH --cpus-per-task=16
#SBATCH --qos=normal

module purge
module load compiler/GCC/10.2.0
module load compiler/GCCcore/10.2.0
module load lang/Python/3.8.6-GCCcore-10.2.0
module load lang/Java/16.0.1
module load math/Gurobi
export PATH=$PATH:$HOME/deps/libminizinc/build
source ~/deps/hpcpy/bin/activate

# Just useful check
print_error_and_exit() { echo "***ERROR*** $*"; exit 1; }
hash parallel 2>/dev/null && test $? -eq 0 || print_error_and_exit "Parallel is not installed on the system"

# Increase the user process limit.
ulimit -u 10000

echo "Node: ${SLURM_NODELIST}"
echo "Executing ${SLURM_NTASKS_PER_NODE} independant tasks at the same time in one node"
export TIMESTAMP=$(date +"%Y%m%dT%H%M%S")


# the --exclusive to srun makes srun use distinct CPUs for each job step
# -N1 -n1 single task with ${SLURM_CPUS_PER_TASK} cores
SRUN="srun  --exclusive -n1 -c ${SLURM_CPUS_PER_TASK:=1} --cpu-bind=cores"

#======================
# Create python
#======================
PYTHON="python"
PYTHON_SCRIPT="main.py"
CORES=$((SLURM_CPUS_PER_TASK / 2))
SOLVER_TIMEOUT=3600
SUMMARY_FILE="../summary_sims_2_objectives_cost_and_clouds.csv"
FIXED_PARAMETERS="--minizinc_data 1 --model_mzn ../mosaic_cloud2.mzn --dzn_dir ../data_sets/ --solver_timeout_sec $SOLVER_TIMEOUT --summary $SUMMARY_FILE --cores $CORES --solver_search_strategy free --fzn_optimisation_level 1"

HOSTNAME=$(hostname)
LOGS="logs.${TIMESTAMP}"
RESUME=""
TASKFILE=""
NTASKS=""
INDEX_FILE_LINES=0


#=======================
# Get Optional arguments
#=======================
while [ $# -ge 1 ]; do
    case $1 in
        -r | --resume)           shift; LOGS=$1; RESUME=" --resume ";;
        -n | --ntasks)           shift; NTASKS="$1"                            ;;
        -* | --*)                echo "[Warning] Invalid option $1"          ;;
        *)                       break                                       ;;
    esac
    shift
done

#=======================
# Get Mandatory  Options
#=======================

if [[ "$#" < 2 ]]; then
    print_error_and_exit "2 arguments are needed, the first one is the taskfile where the parameters are (each line is a set of parameter for runnin the script) and the second one indicates from which line to which line should be executed"
else
    TASKFILE="$1"
    TASKFILE_DIR=$(cd "$(dirname "${TASKFILE}")" && pwd)
    TASKFILE_NAME="$(basename "${TASKFILE}")"
    INDEX_FILE_LINES=$2
fi

echo "Starting parallel worker initialisation on $(hostname)"

#=======================
# Set logs for resuming
#=======================

LOGS_DIR="${TASKFILE_DIR}/${LOGS}"
TASKFILE_MAINLOG="${LOGS_DIR}/${TASKFILE_NAME//sh/log}"
PARALLEL="parallel --delay 0.2 -j ${SLURM_NTASKS} --joblog ${TASKFILE_MAINLOG} ${RESUME}"


echo "Create logs directory if not existing"
mkdir -p ${LOGS_DIR}

ln_start=0
ln_end=0
ln_start=$((INDEX_FILE_LINES * SLURM_NTASKS + 1))
ln_end=$((INDEX_FILE_LINES * SLURM_NTASKS + SLURM_NTASKS_PER_NODE))
sed -n "${ln_start},${ln_end}p" ${TASKFILE} | \
  $PARALLEL eval $SRUN $PYTHON $PYTHON_SCRIPT $FIXED_PARAMETERS {}
