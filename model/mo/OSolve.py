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

    def init_statistics(statistics):
        """This combinator computes these statistics: cp_solution, cp_total_nodes, time_cp_sec, time_fzn_sec, cp_solutions_list."""
        statistics["cp_solutions"] = 0
        statistics["cp_total_nodes"] = 0
        statistics["time_cp_sec"] = 0   # Time spent in the CP solver.
        statistics["time_fzn_sec"] = 0
        statistics["cp_solutions_list"] = []

    @abstractmethod
    def solve(self):
        pass

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