from gurobipy import *
from minizinc import Solver, Instance
from minizinc import Model as ModelMiniZinc

def main():
    model_mzn = "mosaic_cloud2.mzn"
    data_dzn = "./data_sets/paris_30.dzn"
    dict_values = get_values(model_mzn, data_dzn)

def get_values(input_mzn, input_dzn):
    model = ModelMiniZinc(input_mzn)
    model.add_file(input_dzn, parse_data=True)
    mzn_solver = Solver.lookup("gecode")
    # config.initialize_cores(mzn_solver)
    # check_already_computed(config)
    instance = Instance(mzn_solver, model)
    print(instance["num_images"])

if __name__ == "__main__":
  main()