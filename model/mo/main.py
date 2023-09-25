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

from MOMIP import MOMIP
from OSolveMIP import OSolveMIP
from model.mo.FrontGenerators.Gavanelli import Gavanelli
from model.mo.FrontGenerators.Saugmecon import Saugmecon
from model.mo.Solvers.GurobiSolver import GurobiSolver
from model.mo.Solvers.OrtoolsCPSolver import OrtoolsCPSolver


def init_top_level_statistics(statistics):
  statistics["exhaustive"] = False
  statistics["hypervolume"] = 0
  statistics["datetime"] = datetime.now()

def main():
  config = Config()
  model = Model(config.input_mzn)
  model.add_file(config.input_dzn, parse_data=True)
  if config.solver_name == "ortools-py":
    mzn_solver = Solver.lookup("gurobi")
  else:
    mzn_solver = Solver.lookup(config.solver_name)
  config.initialize_cores(mzn_solver)
  check_already_computed(config)
  instance = Instance(mzn_solver, model)
  if config.solver_name == "gurobi" or config.solver_name == "ortools-py":
    instance = get_data_from_minizinc_dzn(instance)
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
  statistics["cp_solutions_list"] = [statistics["cp_solutions_list"][x] for x in pareto_front.front]
  print("end of solving statistics: " + str(statistics))
  write_statistics(config, statistics)

def check_already_computed(config):
  if os.path.exists(config.summary_filename):
    with open(config.summary_filename, 'r') as fsummary:
      summary = csv.DictReader(fsummary, delimiter=';')
      for row in summary:
        if row["instance"] == config.data_name and row["cp_solver"] == config.solver_name and row["front_strategy"] == config.front_strategy and row["cp_strategy"] == config.cp_strategy and row["fzn_optimisation_level"] == str(config.fzn_optimisation_level) and row["cores"] == str(config.cores) and row["cp_timeout_sec"] == str(config.cp_timeout_sec):
         print(f"Skipping {config.uid()} because it is already in {config.summary_filename}")
         exit(0)

def build_solver(instance, config, statistics):
  osolve = build_osolver(instance, config, statistics)
  front_generator_strategy = set_front_strategy(config, instance, osolve)
  osolve_mo = build_MO(instance, statistics, front_generator_strategy, config)
  return osolve_mo, osolve_mo.pareto_front

def build_osolver(instance, config, statistics):
  free_search = config.cp_strategy == "free_search"
  if config.solver_name == "gurobi":
    return GurobiSolver(instance, statistics, config.threads, free_search)
  elif config.solver_name == "ortools-py":
    return OrtoolsCPSolver(instance, statistics, config.threads, free_search)
  else:
    # todo maybe change the name to indicate that this is using MiniZinc
    return OSolveCP(instance, statistics, config.threads, free_search,
                    config.fzn_optimisation_level)

def set_front_strategy(config, instance, solver):
    if config.front_strategy == "saugmecon":
        return Saugmecon(instance, solver, Timer(config.cp_timeout_sec))
    elif config.front_strategy == "gavanelli":
        return Gavanelli(instance, solver, Timer(config.cp_timeout_sec))
    else:
        return Saugmecon(config.cp_strategy, solver, Timer(config.cp_timeout_sec))

def build_MO(instance, statistics, front_generator, config):
  return MOMIP(instance, statistics, front_generator)
  if config.solver_name == "gurobi":
    return MOMIP(instance, statistics, osolve)
  else:
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

def get_data_from_minizinc_dzn(instance, image_id_start=0):
    images = instance["images"]
    costs = instance["costs"]
    areas = instance["areas"]
    clouds = instance["clouds"]
    if image_id_start == 0:  # Minizinc the id starts at 1
        for i in range(len(images)):
          images[i] = {x - 1 for x in images[i]}
        for i in range(len(clouds)):
          clouds[i] = {x - 1 for x in clouds[i]}
    for i in range(len(clouds)):
        if len(clouds[i]) == 0:
          clouds[i] = {}

    max_cloud_area = instance["max_cloud_area"]
    resolution = instance["resolution"]
    incidence_angle = instance["incidence_angle"]

    return InstanceSIMS(images, costs, areas, clouds, max_cloud_area, resolution, incidence_angle)

class InstanceSIMS:
  def __init__(self, images, costs, areas, clouds, max_cloud_area, resolution, incidence_angle):
    self.images = images
    self.costs = costs
    self.areas = areas
    self.clouds = clouds
    self.max_cloud_area = max_cloud_area
    self.resolution = resolution
    self.incidence_angle = incidence_angle
    self.cloud_covered_by_image, self.clouds_id_area = self.get_clouds_covered_by_image()

  def get_clouds_covered_by_image(self):
    cloud_covered_by_image = {}
    clouds_id_area = {}
    for i in range(len(self.clouds)):
      image_cloud_set = self.clouds[i]
      for cloud_id in image_cloud_set:
        if cloud_id not in clouds_id_area:
          clouds_id_area[cloud_id] = self.areas[cloud_id]
        for j in range(len(self.images)):
          if i != j:
            if cloud_id in self.images[j] and cloud_id not in self.clouds[j]:  # the area of the cloud is covered by image j, and it is not cloudy in j
              if j in cloud_covered_by_image:
                cloud_covered_by_image[j].add(cloud_id)
              else:
                cloud_covered_by_image[j] = {cloud_id}
    return cloud_covered_by_image, clouds_id_area

  def get_parts_cloud(self):
    pass


if __name__ == "__main__":
  main()
