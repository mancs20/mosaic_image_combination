from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any


class FrontGeneratorStrategy(ABC):

    def __init__(self, solver, timer):
        self.solver = solver
        self.timer = timer
        self.always_add_new_solutions_to_front()

    @abstractmethod
    def solve(self):
        pass

    @abstractmethod
    def always_add_new_solutions_to_front(self):
        pass

    def get_solver_solution_for_timeout(self, optimize_not_satisfy=True):
        timeout = self.timer.resume()
        print("Start the solver...")
        self.solver.set_time_limit(timeout.total_seconds())
        self.solver.solve(optimize_not_satisfy=False)
        print("Got a result from the solver...")
        solution_sec = self.timer.pause()
        if self.solver.status_time_limit():
            raise TimeoutError()
        return solution_sec

    def prepare_solution(self):
        one_solution = self.solver.get_solution_objective_values()
        solution_values = self.solver.model.get_solution_values()
        ref_points = self.solver.model.get_ref_points_for_hypervolume()
        solution = Solution(objs=one_solution, solution_values=solution_values,
                            minimize_objs=[True] * len(one_solution), ref_point=ref_points)
        status = self.solver.get_status()
        statistics = None
        minizinc_formatted_solution = MinizincResultFormat(status=status, solution=solution, statistics=statistics)
        return minizinc_formatted_solution


@dataclass
class MinizincResultFormat:
    status: None
    solution: Any
    statistics: None

    def __getitem__(self, key):
        if isinstance(self.solution, list):
            if isinstance(key, tuple):
                return getattr(self.solution.__getitem__(key[0]), key[1])
            else:
                return self.solution.__getitem__(key)
        else:
            return getattr(self.solution, key)

@dataclass
class Solution:
    objs: List[int]
    minimize_objs: List[bool]
    solution_values: List[bool]
    ref_point: List[int]


