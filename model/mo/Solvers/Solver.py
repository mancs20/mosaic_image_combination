from abc import ABC, abstractmethod


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

    def solve(self, optimize_not_satisfy=True, verbose=False):
        if len(self.lexicographic_obj_order) == 0:
            self.opt_one_objective_or_satisfy(optimize_not_satisfy=optimize_not_satisfy, verbose=verbose)
        else:
            self.perform_lexicographic_optimization(verbose=verbose)

    @abstractmethod
    def opt_one_objective_or_satisfy(self, optimize_not_satisfy=True, verbose=False):
        pass

    def set_lexicographic_optimization(self, objectives_list_order):
        self.lexicographic_obj_order = objectives_list_order

    @abstractmethod
    def perform_lexicographic_optimization(self, verbose=False):
        pass

    @abstractmethod
    def deactivate_lexicographic_optimization(self):
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
    def remove_constraint(self, constraint):
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

    # numerical resolution of the objective -------------------------------------------------
    # Used by the augmented objective of Saugmecon (see FrontGenerators/SaugmeconAugmentation.py). A solver that works
    # with real numbers (Gurobi, SCIP...) overrides these methods, the CP solvers work with integers and build the
    # augmented objective themselves in build_objective_e_constraint_saugmecon.
    def supports_real_valued_objective(self):
        return False

    def configure_objective_resolution(self, min_difference):
        # set the solver tolerances (gaps...) so that differences >= min_difference are not ignored by the
        # stop criteria of the solver
        pass

    def build_objective_with_delta(self, delta, range_array):
        # augmented objective of Saugmecon: objectives[0] + delta * sum(objectives[i + 1] / range_array[i]). It works
        # with any solver whose expressions accept "+" and "*" by a number
        objective = self.model.objectives[0]
        for other_objective, objective_range in zip(self.model.objectives[1:], range_array):
            if objective_range > 0:
                objective = objective + (delta / objective_range) * other_objective
        self.set_single_objective(objective)
    # ---------------------------------------------------------------------------------------

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
    def objs_smaller_equal_at_least_one_smaller(self, constraints_lhs, rhs, id_constraint=0):
        pass

    @abstractmethod
    def get_nodes_solution(self, solution):
        pass

    def get_flat_time_secs(self, solution):
        return 0
