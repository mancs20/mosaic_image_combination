from abc import ABC, abstractmethod


class OSolve(ABC):
    def __init__(self, instance, statistics, timer, threads=None, free_search=False, optimisation_level=1):
        self.instance = instance
        self.local_constraints = ""
        self.threads = threads
        self.timer = timer
        self.free_search = free_search
        self.optimisation_level = optimisation_level
        self.statistics = statistics
        OSolve.init_statistics(self.statistics)

    @staticmethod
    def init_statistics(statistics):
        """This combinator computes these statistics: number_of_solutions, total_nodes, time_solver_sec,
        minizinc_time_fzn_sec, solutions_time_list."""
        statistics["number_of_solutions"] = 0
        statistics["total_nodes"] = 0
        statistics["time_solver_sec"] = 0   # Time spent in the solver.
        statistics["minizinc_time_fzn_sec"] = 0
        statistics["solutions_time_list"] = []

    @abstractmethod
    def solve(self):
        pass

    @abstractmethod
    def update_statistics(self, res, cp_sec):
        pass
