from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any


class FrontGeneratorStrategy(ABC):

    def __init__(self, solver, timer):
        self.solver = solver
        self.timer = timer
        self.not_evaluate_always_add_new_solutions_to_front = False
        self.solution_incomplete_due_timeout = None

    @abstractmethod
    def solve(self):
        pass

    @abstractmethod
    def always_add_new_solutions_to_front(self):
        pass

    def get_solver_solution_for_timeout(self, optimize_not_satisfy):
        print("Start the solver...")
        timeout = float(self.timer.time_budget_sec)
        # check if the timeout is already reached, sometimes the solver doesn't stop in the exact time that
        # the timeout is reached. For example, if the timeout is 10 seconds, the solver can stop in 10.0001 seconds.
        if timeout <= 0:
            raise TimeoutError()
        self.solver.set_time_limit(timeout)
        self.timer.resume()
        self.solver.solve(optimize_not_satisfy=optimize_not_satisfy)
        solution_sec = self.timer.pause()
        if self.solver.status_time_limit():
            self.deal_with_timeout(solution_sec)
        print("Got a result from the solver...")
        return solution_sec

    def deal_with_timeout(self, solution_sec):
        self.solution_incomplete_due_timeout = self.process_feasible_solution(solution_sec)
        print("Solver timed out...")
        raise TimeoutError()

    def process_feasible_solution(self, solution_sec):
        # update statistics
        self.solver.update_statistics(solution_sec)
        # record the solution
        formatted_solution = self.prepare_solution()
        return formatted_solution

    def prepare_solution(self):
        one_solution = self.solver.get_solution_objective_values()
        solution_values = self.solver.model.get_solution_values()
        ref_points = self.solver.model.get_ref_points_for_hypervolume()
        minimize_objs = [self.solver.model.is_a_minimization_model()] * len(one_solution)
        solution = Solution(objs=one_solution, solution_values=solution_values,
                            minimize_objs=minimize_objs, ref_point=ref_points)
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


