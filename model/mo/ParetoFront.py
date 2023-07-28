from pymoo.indicators.hv import HV
import numpy as np

class ParetoFront:
  """A class representing a Pareto front of solutions over integer variables.

  Attributes:
    instance (Instance): A Minizinc instance containing the model to be solved.
      In particular, the model is expected to have three parameters (where `N` is the number of objectives):
      * `array[1..N] of var int: objs;` are the objectives variables.
      * `array[1..N] of bool: minimize_objs;` where `minimize_objs[i]` is `true` if the objective `i` needs to be minimized and `false` if it needs to be maximized.
      * `array[1..N] of int: ref_point;` (optional): if the hypervolume function is called, `ref_point` is the reference point of the hypervolume, i.e., the worst possible point.
    solutions (List[Result]): All the solutions that has been discovered so far.
    front (List[Int]): An index subset of `solutions` containing the Pareto front. Invariant: front is sorted.
  """

  def __init__(self, instance):
    self.instance = instance
    self.minimize_objs = []
    self.solutions = []
    self.front = []

  def num_found_solutions(self):
    return len(self.solutions)

  def compare(self, obj1, obj2, minimize):
    """Compare two objectives value according to `minimize`.
        Returns:
          Bool:
            `True` if the objective `obj1` is smaller or equal to `obj2` in case of minimization,
            or if `obj1` is greater or equal to `obj2` in case of maximization. `False` otherwise.
    """
    if minimize:
      return obj1 <= obj2
    else:
      return obj1 >= obj2

  def dominates(self, x, y):
    """Compare two solutions according to their objectives values.
        Args:
          x (Solution): A solution to the constraint model described by `instance`.
          y (Solution): A solution to the constraint model described by `instance`.
        Returns:
          Bool:
            `True` if `x` dominates or is equal to `y`, `False` otherwise.
    """
    return all([self.compare(int(obj1), int(obj2), m) for (obj1, obj2, m) in zip(x['objs'], y['objs'], x['minimize_objs'])])

  def join_front(self, idx):
    """Update the Pareto front with the solution `self.solutions[idx]` if it is not dominated by any solution.
        Args:
          idx (Int): The index of the solution to be added to the Pareto front.
        Returns:
          Bool:
            `True` if `x` was added to the solutions set and the Pareto front, `False` otherwise.
    """
    for idf, f in enumerate(self.front):
      if self.dominates(self.solutions[f], self.solutions[idx]):
        return False
      elif self.dominates(self.solutions[idx], self.solutions[f]):
        self.front.pop(idf)
    self.front.append(idx)
    return True

  def join(self, x):
    """Add to the Pareto front the solution `x` if it is not dominated by any solution in the Pareto front.
       The Pareto front is also updated to remove all solutions dominated by `x`.
        Args:
          x (Result): A solution to the constraint model described by `instance`.
        Returns:
          Bool:
            `True` if `x` was added to the solutions set and the Pareto front, `False` otherwise.
    """
    idx = len(self.solutions)
    self.solutions.append(x)

    if not self.join_front(idx):
      # self.solutions.pop()
      return False
    return True

  def join_without_pareto_verification(self, x):
    """Add to the Pareto front the solution `x` without checking if it is dominated by any solution in the Pareto front.
       The Pareto front is also updated to remove all solutions dominated by `x`.
        Args:
          x (Result): A solution to the constraint model described by `instance`.
        Returns:
          Bool:
            `True` if `x` was added to the solutions set and the Pareto front, `False` otherwise.
    """
    idx = len(self.solutions)
    self.solutions.append(x)
    self.front.append(idx)
    return True

  def remove(self, x):
    """Remove the solution `x` from the Pareto front, and recompute the Pareto front without `x`.
       The same Pareto front is obtained if `x` is not in the Pareto front.
       Args:
          x (Result): A solution to the constraint model described by `instance`.
       Returns:
          Bool:
            `True` if `x` was removed from the Pareto front, `False` otherwise.
    """
    idx_x = self.solutions.index(x)
    if idx_x not in self.front:
      return False
    # All solutions in the front added after `x` are not dominated by `x` (otherwise `x` is not in the Pareto front).
    self.front = [f for f in self.front if f > idx_x]
    for idx_y in range(0, idx_x):
      self.join_front(idx_y)
    self.front.sort()
    return True

  def filter(self, keep):
    """Update the Pareto front of the solutions set such that all solutions in the Pareto front satisfy the predicate `keep`.
       It is a generator that yields the solutions satisfying the predicate `keep`.

       Args:
          keep (Result -> Bool): A predicate on solutions returning `True` if the solution must be kept, and `False` otherwise.
        Returns:
          Result:
            The solutions satisfying the predicate `keep`.
    """
    if self.front == []:
      return
    idx = self.front[-1]
    while idx >= 0:
      if not keep(self.solutions[idx]):
        self.remove(self.solutions[idx])
      else:
        yield self.solutions[idx]
      remaining_front = [f for f in self.front if f < idx]
      if len(remaining_front) == 0:
        idx = -1
      else:
        idx = remaining_front[-1]

  def not_dominated_constraint_mzn(self, x):
    """For each solution `y` to the problem, we return a Minizinc constraint guaranteeing that `y` is not dominated by `x`.
       Returns:
        Str:
          For instance, on a bi-objective problem `objs[1] > 1 \/ objs[2] < 10`
    """
    cons = []
    for i, minimize in enumerate(x['minimize_objs']):
      obj_value = int(x["objs"][i])
      if minimize:
        cons.append(f"objs[{i+1}] < {obj_value}")
      else:
        cons.append(f"objs[{i+1}] > {obj_value}")
    return " \\/ ".join(cons)

  def front_constraint_mzn(self):
    """For each solution `y` to the problem, we return a Minizinc constraint guaranteeing that `y` is not dominated by any solution in the Pareto front.
        Returns:
          Str:
            For instance, on a bi-objective problem with two elements in the front `(objs[1] > 1 \/ objs[2] < 10) /\ (objs[1] > 5 \/ objs[2] < 15)`
            If the front is empty, we return `true`.
    """
    if self.front == []:
      return "true"
    cons = []
    for f in self.front:
      cons.append("(" + self.not_dominated_constraint_mzn(self.solutions[f]) + ")")
    return " /\\ ".join(cons)

  def to_str(self):
    """Return a string representation of the Pareto front."""
    return '{' + ','.join([str(self.solutions[f]['objs']) for f in self.front]) + '}'

  def solutions_to_str(self):
    """Return a string representation of the solutions in the Pareto front."""
    temp_solutions = []
    for f in self.front:
      sol_f = []
      for idx, val in enumerate(self.solutions[f]['taken']):
        if val:
          sol_f.append(idx)
      temp_solutions.append(str(sol_f))
    return '{' + ','.join(temp_solutions) + '}'

  def ef_arr_to_str(self):
    """Return a string representation of the ef_array used to ger the solution in the Pareto front."""
    ef_arrays = []
    for f in self.front:
      ef_arrays.append(str(self.solutions[f]['ef_array']))
    return '{' + ','.join(ef_arrays) + '}'

  def hypervolume(self):
    """Compute the hypervolume of the Pareto front. The hypervolume is computed using the reference point `ref_point`."""
    if self.front == []:
      return 0
    ref_point = np.array(self.solutions[0]["ref_point"])
    front = np.array([self.solutions[f]['objs'] for f in self.front])
    for minimize in self.solutions[0]["minimize_objs"]:
      if not minimize:
        assert False, ("We only support minimization for now.")
    return HV(ref_point=ref_point)(front)
