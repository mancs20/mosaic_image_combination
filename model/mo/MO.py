from ParetoFront import *

class MO:
  """Multi-objective solver maintining a Pareto front.
     See further information in the class `ParetoFront`.
  Args:
    instance (Instance): A constraint model.
    subsolver (Solver): A solver for the constraint model instance supporting `solve()` and `add_local_constraint()`.
    verbose (Bool): If `True`, the solver prints the Pareto front, new objectives and statistics at each iteration."""
  def __init__(self, instance, statistics, subsolver, verbose = True):
    self.instance = instance
    self.subsolver = subsolver
    self.pareto_front = ParetoFront(instance)
    self.verbose = verbose
    self.statistics = statistics
    MO.init_statistics(statistics)

  def init_statistics(statistics):
    statistics["pareto_front"] = ""

  def solve(self):
    for x in self.subsolver.solve():
      self.pareto_front.join(x)
      if self.verbose:
        print("New objective found: " + str(x["objs"]))
        print(self.pareto_front.to_str())
        self.statistics["pareto_front"] = self.pareto_front.to_str()
        print(self.pareto_front.front_constraint_mzn())
        print(x.statistics)
      yield x
      self.subsolver.add_local_constraint(self.pareto_front.front_constraint_mzn())

  def add_local_constraint(self, constraint):
    self.subsolver.add_local_constraint(constraint)

  def add_global_constraint(self, constraint):
    self.subsolver.add_global_constraint(constraint)
