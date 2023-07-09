from Config import *
from Sequence import *
from MOCP import *
from OSolveCP import *
from Timer import *
from minizinc import Instance, Model, Solver
import csv
import os
import traceback
import logging
from filelock import FileLock, Timeout

from model.mo.OSolveMIP import OSolveMIP


def init_top_level_statistics(statistics):
  statistics["exhaustive"] = False
  statistics["hypervolume"] = 0
  statistics["datetime"] = datetime.now()

def main():
  config = Config()
  model = Model(config.input_mzn)
  model.add_file(config.input_dzn, parse_data=True)
  mzn_solver = Solver.lookup(config.solver_name)
  config.initialize_cores(mzn_solver)
  check_already_computed(config)
  instance = Instance(mzn_solver, model)
  print("Start computing: " + config.uid())
  statistics = {}
  config.init_statistics(statistics)
  init_top_level_statistics(statistics)
  solver, pareto_front = build_solver(instance, config, statistics)
  try:
    statistics["exhaustive"] = False
    for x in solver.solve():
      pass
    print("Problem completely explored.")
    statistics["exhaustive"] = True
  except TimeoutError:
    print("Timeout triggered")
  except Exception as e:
    print("Execption raised: " + str(e))
    logging.error(traceback.format_exc())
  statistics["hypervolume"] = pareto_front.hypervolume()
  print("end of solving statistics: " + str(statistics))
  write_statistics(config, statistics)

def check_already_computed(config):
  if os.path.exists(config.summary_filename):
    with open(config.summary_filename, 'r') as fsummary:
      summary = csv.DictReader(fsummary, delimiter=';')
      for row in summary:
        if row["instance"] == config.data_name and row["cp_solver"] == config.solver_name and row["cp_strategy"] == config.cp_strategy and row["fzn_optimisation_level"] == str(config.fzn_optimisation_level) and row["cores"] == str(config.cores) and row["cp_timeout_sec"] == str(config.cp_timeout_sec):
         print(f"Skipping {config.uid()} because it is already in {config.summary_filename}")
         exit(0)

def build_solver(instance, config, statistics):
  osolve = build_osolver(instance, config, statistics)
  osolve_mo = build_MO(instance, statistics, osolve, config)
  return osolve_mo, osolve_mo.pareto_front

def build_osolver(instance, config, statistics):
  free_search = config.cp_strategy == "free_search"
  if config.solver_name == "gurobi":
    return OSolveMIP(instance, statistics, Timer(config.cp_timeout_sec), config.threads, free_search)
  else:
    return OSolveCP(instance, statistics, Timer(config.cp_timeout_sec), config.threads, free_search, config.fzn_optimisation_level)

def build_MO(instance, statistics, osolve, config):
  if config.solver_name == "gurobi":
    return MOCP(instance, statistics, osolve)
  else:
    return MOCP(instance, statistics, osolve)

def csv_header(config):
  statistics = {}
  config.init_statistics(statistics)
  init_top_level_statistics(statistics)
  OSolveCP.init_statistics(statistics)
  MOCP.init_statistics(statistics)
  return list(statistics.keys())

def create_summary_file(config):
  """We create the CSV summary file if it does not exist yet.
     The header of the summary file is the list of all the statistics the combinators can collect, even if the current solving algorithm do not use all of them.
     This is to be able to compare the statistics of different algorithms.
  """
  if not os.path.exists(config.summary_filename):
    with open(config.summary_filename, "w") as summary:
      writer = csv.DictWriter(summary, fieldnames=csv_header(config), delimiter=';')
      writer.writeheader()

def statistics_to_csv(config, statistics):
  stats_keys = csv_header(config)
  csv_entry = ""
  for k in stats_keys:
    if k in statistics:
      csv_entry += str(statistics[k])
    csv_entry += ";"
  return csv_entry[:-1] + "\n"

def write_statistics(config, statistics):
  try:
    lock = FileLock(config.summary_filename + ".lock", timeout=10)
    with lock:
      create_summary_file(config)
      with open(config.summary_filename, "a") as summary:
        summary.write(statistics_to_csv(config, statistics))
  except Timeout:
    print("Could not acquire lock on summary file. Statistics will be printed on standard output instead.")
    print(statistics_to_csv(config, statistics))

if __name__ == "__main__":
  main()
