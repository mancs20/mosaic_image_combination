#!/bin/bash

# Get the value from line 7 of "gnu_parallel_launcher_experiments.sh"
ntasks_per_node=$(sed -n '7s/.*=//p' gnu_parallel_launcher_experiments.sh)

# Calculate the number of jobs
number_of_lines=$(wc -l < gnu_parallel_experiment_parameters)
# number of jobs is equal to the upper bound of the number_of_lines / ntasks_per_node
number_of_jobs=$(( (number_of_lines + ntasks_per_node - 1) / ntasks_per_node ))

# Iterate over the number of jobs and submit Slurm jobs
for idx in $(seq 0 $((number_of_jobs - 1))); do
    sbatch gnu_parallel_launcher_experiments.sh gnu_parallel_experiment_parameters "$idx"
done