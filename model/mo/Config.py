import os
import argparse
import multiprocessing

class Config:
  """Configuration class for the multi-objective constraint programming.
     It parses the commandline arguments and initializes the temporary and result directories."""
  def __init__(self):
    parser = argparse.ArgumentParser(
                prog = 'multi_objective_cp',
                description = 'Multi-objective constraint programming. This program computes a Pareto front of an optimization constraint problem.')
    parser.add_argument('instance_name')
    parser.add_argument('--model_mzn', required=True)
    parser.add_argument('--dzn_dir', required=True)
    parser.add_argument('--problem_name', required=True)
    parser.add_argument('--solver_name', required=True)
    parser.add_argument('--front_strategy', required=True)
    parser.add_argument('--cp_timeout_sec', required=True, type=int)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--cores', type=int)
    parser.add_argument('--cp_strategy', required=True)             # Must be "free" or the name of a CP strategy (only for information purposes, the strategy must be described in the model).
    parser.add_argument('--fzn_optimisation_level', required=True, type=int)
    args = parser.parse_args()
    Config.clean_dir_name(args.dzn_dir)
    self.data_name = args.instance_name
    self.input_mzn = args.model_mzn
    self.cp_model = os.path.basename(self.input_mzn)[:-4]
    self.input_dzn = args.dzn_dir + "/" + self.data_name + ".dzn"
    self.solver_name = args.solver_name
    self.problem_name = args.problem_name
    self.front_strategy = args.front_strategy
    self.cp_timeout_sec = args.cp_timeout_sec
    self.summary_filename = args.summary
    self.cp_strategy = args.cp_strategy
    self.fzn_optimisation_level = args.fzn_optimisation_level
    self.cores = args.cores

  def clean_dir_name(dir):
    """Remove the last '/' if it exists."""
    if dir[-1] == '/':
      dir = dir[:-1]

  def init_statistics(self, statistics):
    statistics["instance"] = self.data_name
    statistics["problem"] = self.problem_name
    statistics["solver_name"] = self.solver_name
    statistics["front_strategy"] = self.front_strategy
    statistics["cp_strategy"] = self.cp_strategy
    statistics["fzn_optimisation_level"] = self.fzn_optimisation_level
    statistics["threads"] = self.threads
    statistics["cores"] = self.cores
    statistics["cp_timeout_sec"] = self.cp_timeout_sec
    statistics["cp_model"] = self.cp_model

  def uid(self):
    """Unique identifier for this experiment."""
    return self.data_name + "_" + self.problem_name + "_" + self.solver_name + "_" + self.front_strategy + "_" + self.cp_model + "_" + self.cp_strategy + "_" + str(self.cp_timeout_sec) + "_" + str(self.fzn_optimisation_level) + "_" + str(self.cores)

  def initialize_cores(self, solver):
    """If the solver supports parallelization, use twice the number of available cores. Otherwise, use only one core."""
    if "-p" in solver.stdFlags:
      if self.cores is None:
        self.cores = multiprocessing.cpu_count()
      self.threads = self.cores * 2
    else:
      self.cores = 1
      self.threads = 1
