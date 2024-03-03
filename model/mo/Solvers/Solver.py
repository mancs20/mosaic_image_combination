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
        self.lexicographic_obj_order = []
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
        statistics["number_of_solutions"] = 0
        statistics["total_nodes"] = 0
        statistics["time_solver_sec"] = 0
        statistics["minizinc_time_fzn_sec"] = 0
        statistics["solutions_time_list"] = []

    def solve(self, optimize_not_satisfy=True):
        if len(self.lexicographic_obj_order) == 0:
            self.opt_one_objective_or_satisfy(optimize_not_satisfy=optimize_not_satisfy)
        else:
            self.perform_lexicographic_optimization()

    @abstractmethod
    def opt_one_objective_or_satisfy(self, optimize_not_satisfy=True):
        pass

    def set_lexicographic_optimization(self, objectives_list_order):
        self.lexicographic_obj_order = objectives_list_order
        self.set_single_objective(self.model.objectives[objectives_list_order[0]])

    @abstractmethod
    def perform_lexicographic_optimization(self):
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
    def add_constraints_geq(self, constraint, rhs):
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
    def build_objective_e_constraint_saugmecon(self, range_array, augmentation):
        pass

    @abstractmethod
    def build_objective_e_constraint_augmecon2(self, best_constrain_obj_list, nadir_constrain_obj_list, augmentation):
        pass

    @abstractmethod
    def change_objective_sense(self, id_objective):
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
        solution = self.get_complete_solution()
        if solution is None:
            return
        self.statistics["minizinc_time_fzn_sec"] = self.get_flat_time_secs(solution)
        self.statistics["number_of_solutions"] += 1
        self.statistics["total_nodes"] += self.get_nodes_solution(solution)
        self.statistics["time_solver_sec"] += seconds
        self.statistics["solutions_time_list"].append(self.statistics["time_solver_sec"])

    @abstractmethod
    def get_complete_solution(self):
        pass

    @abstractmethod
    def add_or_all_objectives_constraint(self, rhs, id_constraint=0):
        pass

    @abstractmethod
    def get_nodes_solution(self, solution):
        pass

    def get_flat_time_secs(self, solution):
        return 0
