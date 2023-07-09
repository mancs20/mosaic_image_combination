from ParetoFront import *
from model.mo.MO import MO


class MOCP(MO):
  """Multi-objective solver maintaining a Pareto front.
     See further information in the class `ParetoFront`.
  Args:
    instance (Instance): A constraint model.
    statistics (dict): A dictionary to store the statistics of the solver.
    subsolver (Solver): A solver for the constraint model instance supporting `solve()` and `add_local_constraint()`.
    verbose (Bool): If `True`, the solver prints the Pareto front, new objectives and statistics at each iteration."""
  def __init__(self, instance, statistics, subsolver, verbose = True):
    super().__init__(instance, statistics, subsolver, verbose = True)

    # self.instance = instance
    # self.subsolver = subsolver
    # self.pareto_front = ParetoFront(instance)
    # self.verbose = verbose
    # self.statistics = statistics
    # self.init_statistics()

  def solve(self):
    for x in self.subsolver.solve():
      self.pareto_front.join(x)
      self.statistics["pareto_front"] = self.pareto_front.to_str()
      if self.verbose:
        print("New objective found: " + str(x["objs"]))
        print(self.statistics["pareto_front"])
        print(self.pareto_front.front_constraint_mzn())
        print(x.statistics)
      yield x
      self.subsolver.add_local_constraint(self.pareto_front.front_constraint_mzn())

  def add_local_constraint(self, constraint):
    self.subsolver.add_local_constraint(constraint)

  def add_global_constraint(self, constraint):
    self.subsolver.add_global_constraint(constraint)
