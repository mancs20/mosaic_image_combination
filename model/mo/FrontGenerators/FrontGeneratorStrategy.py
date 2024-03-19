from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any


class FrontGeneratorStrategy(ABC):

    def __init__(self, solver, timer):
        self.solver = solver
        self.timer = timer
        self.best_objective_values = None
        self.nadir_objectives_values = None
        self.front_solutions = []
        self.not_evaluate_always_add_new_solutions_to_front = False
        self.solution_incomplete_due_timeout = None
        if self.solver.model.is_a_minimization_model():
            self.model_optimization_sense = "min"
            self.step = -1
        else:
            self.model_optimization_sense = "max"
            self.step = 1

    @abstractmethod
    def solve(self):
        pass

    @abstractmethod
    def always_add_new_solutions_to_front(self):
        pass

    def get_solver_solution_for_timeout(self, optimize_not_satisfy, verbose=False):
        print("Start the solver...")
        timeout = float(self.timer.time_budget_sec)
        # check if the timeout is already reached, sometimes the solver doesn't stop in the exact time that
        # the timeout is reached. For example, if the timeout is 10 seconds, the solver can stop in 10.0001 seconds.
        if timeout <= 0:
            raise TimeoutError()
        self.solver.set_time_limit(timeout)
        self.timer.resume()
        self.solver.solve(optimize_not_satisfy=optimize_not_satisfy, verbose=verbose)
        solution_sec = self.timer.pause()
        if self.solver.status_time_limit():
            self.deal_with_timeout(solution_sec)
        print("Got a result from the solver...")
        return solution_sec

    def deal_with_timeout(self, solution_sec):
        try:
            self.solution_incomplete_due_timeout = self.process_feasible_solution(solution_sec)
        except Exception as e:
            print("Couldn't get the last incomplete solution")
        print("Solver timed out...")
        raise TimeoutError()

    def process_feasible_solution(self, solution_sec):
        # update statistics
        self.solver.update_statistics(solution_sec)
        # record the solution
        formatted_solution = self.prepare_solution()
        return formatted_solution

    def prepare_solution(self, one_solution=None, solution_values=None):
        if one_solution is None:
            one_solution = self.solver.get_solution_objective_values()
        if solution_values is None:
            solution_values = self.solver.model.get_solution_values()
        ref_points = self.solver.model.get_ref_points_for_hypervolume()
        minimize_objs = [self.solver.model.is_a_minimization_model()] * len(one_solution)
        solution = Solution(objs=one_solution, solution_values=solution_values,
                            minimize_objs=minimize_objs, ref_point=ref_points)
        status = self.solver.get_status()
        statistics = None
        minizinc_formatted_solution = MinizincResultFormat(status=status, solution=solution, statistics=statistics)
        return minizinc_formatted_solution

    def get_nadir_objectives(self):
        nadir_objectives = self.solver.model.get_nadir_bound_estimation()
        return nadir_objectives

    def get_ideal_objectives(self):
        ideal_objectives = self.solver.model.get_ideal_bound_estimation()
        return ideal_objectives

    def get_best_worst_for_2obj_lexicographically(self):
        if len(self.solver.model.objectives) != 2:
            raise Exception("Error. get_best_worst_for_2obj_lexicographically method was called for a problem with "
                            "more thant 2 objectives.")
        self.best_objective_values = [0] * len(self.solver.model.objectives)
        self.nadir_objectives_values = [0] * len(self.solver.model.objectives)
        for i in range(len(self.solver.model.objectives)):
            if i == 0:
                obj_lexicographic = [0, 1]
                j = 1
            else:
                j = 0
                obj_lexicographic = [1, 0]
            self.solver.set_lexicographic_optimization(obj_lexicographic)
            self.solver.set_optimization_sense(self.model_optimization_sense)
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=True)
            formatted_solution = self.process_feasible_solution(solution_sec)
            self.front_solutions.append(formatted_solution)
            yield formatted_solution
            self.best_objective_values[i] = formatted_solution['objs'][i]
            self.nadir_objectives_values[j] = formatted_solution['objs'][j]
        self.solver.lexicographic_obj_order = []


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
