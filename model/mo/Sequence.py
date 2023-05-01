from datetime import datetime

class Sequence:
  """A sequence of constraint solvers called one after the other.
     Args:
       subsolvers (List[Solver]): A list of solvers to be ran in sequence.
       local_timeout (Bool): If `True`, a timeout on a solver is considered local and the next solver is still ran.
         `TimeoutError` is still raised at the end of the sequence if one local timeout was reached."""
  def __init__(self, subsolvers, local_timeout = True):
    self.subsolvers = subsolvers
    self.active_subsolver = self.subsolvers[0]
    self.local_timeout = local_timeout
    self.one_timeout = False

  def solve(self):
    """Yields all solutions of each solver in turn."""
    for s in self.subsolvers:
      self.active_subsolver = s
      try:
        for x in s.solve():
          yield x
      except TimeoutError:
        self.one_timeout = True
        if not self.local_timeout:
          raise
    if self.one_timeout:
      raise TimeoutError

  def add_local_constraint(self, constraint):
    """Adds a local constraint to the solver currently active in `solve`."""
    self.active_subsolver.add_local_constraint(constraint)

  def add_global_constraint(self, constraint):
    """Adds a constraint to all solvers in the sequence."""
    for s in self.subsolvers:
      s.add_global_constraint(constraint)
