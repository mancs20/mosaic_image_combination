from minizinc import Status
import minizinc

class OSolve:
  """A constraint programming solver repeatedly solving a constraint model without modifying it.
     It is aimed to be used with other combinators that update the problem.
     Args:
       instance (Instance): A constraint model.
       statistics (dict): A dictionary to store the statistics of the solver.
       timer (Timer): A timer to retrieve the remaining time budget.
       cores (Optional[Int]): The number of cores to use. `None` for single-threaded solving.
       free_search (Optional[Bool]): Whether to use the free search of the underlying solver and ignore model search annotations.
       optimisation_level (Int): The optimisation level of the preprocessing step when converting MiniZinc to FlatZinc (from 1 to 5). Note that this is done before each call to `solve`.
  """

  def __init__(self, instance, statistics, timer, threads=None, free_search=False, optimisation_level=1):
    self.instance = instance
    self.local_constraints = ""
    self.threads = threads
    self.timer = timer
    self.free_search = free_search
    self.optimisation_level = optimisation_level
    self.statistics = statistics
    OSolve.init_statistics(self.statistics)

  def init_statistics(statistics):
    """This combinator computes these statistics: cp_solution, cp_total_nodes, time_cp_sec, time_fzn_sec, cp_solutions_list."""
    statistics["cp_solutions"] = 0
    statistics["cp_total_nodes"] = 0
    statistics["time_cp_sec"] = 0
    statistics["time_fzn_sec"] = 0
    statistics["cp_solutions_list"] = []

  def solve(self):
    """Solve the constraint model described by `instance` with the local constraints and yield all solutions found.
       Between two consecutive calls to `solve`, the constraint model should be modified, otherwise the same solution might be returned.
       The local constraints are reset after each call to `solve`.
       Raises:
          TimeoutError: If the time budget is exhausted.
       Returns:
         Solution:
           A solution to `instance`."""
    while True:
      timeout = self.timer.resume()
      with self.instance.branch() as child:
        child.add_string(self.local_constraints)
        self.local_constraints = ""
        while True:
          try:
            print("Start the CP solver...")
            res = child.solve(
              optimisation_level = self.optimisation_level,
              all_solutions = False,
              free_search = self.free_search,
              timeout = timeout,
              processes = self.threads)
            print("Got a result from the CP solver...")
            break
          except minizinc.error.MiniZincError:
            print("The solver crashed... Retrying...") # It can happen with GeCode in parallel mode.
      cp_sec = self.timer.pause()
      self.update_statistics(res, cp_sec)
      if res.status == Status.SATISFIED or res.status == Status.ALL_SOLUTIONS:
        yield res
      elif res.status == Status.UNKNOWN: # timeout
        raise TimeoutError()
      elif res.status == Status.ERROR:
        raise Exception("CP solver error\n")
      else:
        break

  def add_local_constraint(self, constraint):
    """Add a constraint to the model only for the next call to `solve`."""
    if constraint != "true":
      self.local_constraints += "constraint " + constraint + ";\n"

  def add_global_constraint(self, constraint):
    """Add a constraint to the model persisting between calls to `solve`."""
    if constraint != "true":
      self.instance.add_string("constraint " + constraint + ";\n")

  def update_statistics(self, res, cp_sec):
    self.statistics["time_cp_sec"] += cp_sec
    if res is None:
      return
    if "nodes" in res.statistics:
      self.statistics["cp_total_nodes"] += res.statistics["nodes"]
    if "flatTime" in res.statistics:
      self.statistics["time_fzn_sec"] += res.statistics["flatTime"].total_seconds()
    if res.solution is not None:
      self.statistics["cp_solutions"] += 1
      self.statistics["cp_solutions_list"].append(self.statistics["time_cp_sec"])
