from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any


class Solver(ABC):
    def __init__(self, model, statistics, threads, free_search=True):
        self.model = model
        self.assert_right_solver(model)
        self.solver = self.set_solver()
        self.free_search = free_search
        self.statistics = statistics
        self.set_threads(threads)
        Solver.init_statistics(statistics)

    @abstractmethod
    def assert_right_solver(self, model):
        pass

    def message_incorrect_solver(self):
        return f"Incorrect solver {self} for model {self.model}"

    @abstractmethod
    def set_solver(self):
        pass

    @abstractmethod
    def set_threads(self, threads):
        pass

    @staticmethod
    def init_statistics(statistics):
        # todo remove the cp_ part from the statistics names
        statistics["cp_solutions"] = 0
        statistics["cp_total_nodes"] = 0
        statistics["time_cp_sec"] = 0
        statistics["time_fzn_sec"] = 0
        statistics["cp_solutions_list"] = []

    @abstractmethod
    def solve(self, optimize_not_satisfy = True):
        pass

    def set_optimization_sense(self, sense):
        if sense == "min":
            self.set_minimization()
        elif sense == "max":
            self.set_maximization()
        else:
            raise ValueError("Invalid optimization sense: " + sense)

    @abstractmethod
    def add_constraints_leq(self, constraint, rhs):
        pass

    @abstractmethod
    def remove_constraints(self, constraint):
        pass

    @abstractmethod
    def set_minimization(self):
        pass

    @abstractmethod
    def set_maximization(self):
        pass

    @abstractmethod
    def set_time_limit(self, timeout):
        pass

    @abstractmethod
    def set_single_objective(self, objective_expression):
        pass

    @abstractmethod
    def build_objective_e_constraint_saugmecon(self, range_array):
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def get_solution_objective_values(self):
        pass

    # status---------------------------------------------------
    @abstractmethod
    def get_status(self):
        pass

    @abstractmethod
    def status_time_limit(self):
        pass

    @abstractmethod
    def status_infeasible(self):
        pass
    # status end-------------------------------------------------

    def update_statistics(self, seconds):
        # todo remove the cp_ part from the statistics names
        self.statistics["time_cp_sec"] += seconds
        solution = self.get_complete_solution()
        if solution is None:
            return
        self.statistics["cp_solutions"] += 1
        self.statistics["cp_total_nodes"] += self.get_nodes_solution(solution)
        self.statistics["time_cp_sec"] += seconds
        self.statistics["cp_solutions_list"].append(self.statistics["time_cp_sec"])

    @abstractmethod
    def get_complete_solution(self):
        pass

    @abstractmethod
    def get_nodes_solution(self, solution):
        pass



