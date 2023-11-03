import constants
from Config import *
from MOCP import *
from OSolveCP import *
from Timer import *
from minizinc import Instance, Model, Solver
import csv
import os
import traceback
import logging
from filelock import FileLock, Timeout

from MONoMinizinc import MONoMinizinc
from model.mo.FrontGenerators.Gavanelli import Gavanelli
from model.mo.FrontGenerators.Saugmecon import Saugmecon
from model.mo.Instances.InstanceMinizinc import InstanceMinizinc
from model.mo.Instances.InstanceSIMS import InstanceSIMS
from model.mo.Solvers.GurobiModels.SatelliteImageMosaicSelectionGurobiModel import \
  SatelliteImageMosaicSelectionGurobiModel
from model.mo.Solvers.GurobiSolver import GurobiSolver
from model.mo.Solvers.OrtoolsCPModels.SatelliteImageMosaicSelectionOrtoolsCPModel import \
  SatelliteImageMosaicSelectionOrtoolsCPModel
from model.mo.Solvers.OrtoolsCPSolver import OrtoolsCPSolver


def init_top_level_statistics(statistics):
  statistics["exhaustive"] = False
  statistics["hypervolume"] = 0
  statistics["datetime"] = datetime.now()

def main():
  config = Config()
  instance = build_instance(config)
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
  solution_times_list = [statistics["solutions_time_list"][x] for x in pareto_front.front]
  statistics["solutions_time_list"] = solution_times_list
  print("end of solving statistics: " + str(statistics))
  write_statistics(config, statistics)

def build_instance(config):
  # here we build the instance, it could from minizinc or from other format
  model = Model(config.input_mzn)
  model.add_file(config.input_dzn, parse_data=True)
  if config.solver_name == "ortools-py":
    mzn_solver = Solver.lookup("gurobi")
  else:
    mzn_solver = Solver.lookup(config.solver_name)
  config.initialize_cores(mzn_solver)
  check_already_computed(config)
  instance = Instance(mzn_solver, model)
  problem_name = config.problem_name
  if config.solver_name == "gurobi" or config.solver_name == "ortools-py":
    if problem_name == constants.Problem.SATELLITE_IMAGE_SELECTION_PROBLEM.value:
      instance = InstanceSIMS(instance)
  else:
    instance = InstanceMinizinc(mzn_solver, model, problem_name)

  return instance

def check_already_computed(config):
  if os.path.exists(config.summary_filename):
    with open(config.summary_filename, 'r') as fsummary:
      summary = csv.DictReader(fsummary, delimiter=';')
      for row in summary:
        if row["instance"] == config.data_name and row["problem"] == config.problem_name and row["solver_name"] == config.solver_name and row["front_strategy"] == config.front_strategy and row["solver_search_strategy"] == config.solver_search_strategy and row["fzn_optimisation_level"] == str(config.fzn_optimisation_level) and row["cores"] == str(config.cores) and row["solver_timeout_sec"] == str(config.solver_timeout_sec):
         print(f"Skipping {config.uid()} because it is already in {config.summary_filename}")
         exit(0)

def build_solver(instance, config, statistics):
  if not instance.is_minizinc:
    model = build_model(instance, config)
  else:
    model = None
  osolve = build_osolver(model, instance, config, statistics)
  front_generator_strategy = set_front_strategy(config, osolve)
  osolve_mo = build_MO(instance, statistics, front_generator_strategy, osolve)
  return osolve_mo, osolve_mo.pareto_front

def build_model(instance, config):
  problem = instance.problem_name
  if not instance.is_minizinc:
    if problem == constants.Problem.SATELLITE_IMAGE_SELECTION_PROBLEM.value:
      if config.solver_name == "gurobi":
        return SatelliteImageMosaicSelectionGurobiModel(instance)
      elif config.solver_name == "ortools-py":
        return SatelliteImageMosaicSelectionOrtoolsCPModel(instance)
  else:
    print("Error. You're trying to build a model from a Minizinc instance. Minizinc instances already have the model")
    exit(1)


def build_osolver(model, instance, config, statistics):
  free_search = config.solver_search_strategy == "free_search"
  if instance.is_minizinc:
    # todo maybe change the name to indicate that this is using MiniZinc
    return OSolveCP(instance, statistics, config.threads, free_search,
                    config.fzn_optimisation_level)
  else:
    if config.solver_name == "gurobi":
      return GurobiSolver(model, statistics, config.threads, free_search)
    elif config.solver_name == "ortools-py":
      return OrtoolsCPSolver(model, statistics, config.threads, free_search)
    else:
      return GurobiSolver(model, statistics, config.threads, free_search)

def set_front_strategy(config, solver):
    if config.front_strategy == "saugmecon":
        return Saugmecon(solver, Timer(config.solver_timeout_sec))
    elif config.front_strategy == "gavanelli":
        return Gavanelli(solver, Timer(config.solver_timeout_sec))
    else:
        return Saugmecon(solver, Timer(config.solver_timeout_sec))

def build_MO(instance, statistics, front_generator, osolve):
  if instance.problem_name == constants.Problem.SATELLITE_IMAGE_SELECTION_PROBLEM.value:
    return MONoMinizinc(instance, statistics, front_generator)
  elif instance.problem_name == constants.Problem.MINIZINC_DEFINED:
    # todo check how to remove osolve for minizinc problem, and use front_generator instead
    return MOCP(instance, statistics, osolve)

def csv_header(config):
  statistics = {}
  config.init_statistics(statistics)
  init_top_level_statistics(statistics)
  OSolve.init_statistics(statistics)
  MO.init_statistics(statistics)
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
