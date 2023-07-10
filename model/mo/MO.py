from abc import ABC, abstractmethod

from ParetoFront import ParetoFront


class MO(ABC):

    def __init__(self, instance, statistics, subsolver, verbose=True):
        self.instance = instance
        self.subsolver = subsolver
        self.pareto_front = ParetoFront(instance)
        self.verbose = verbose
        self.statistics = statistics
        MO.init_statistics(statistics)

    def init_statistics(statistics):
        statistics["pareto_front"] = ""
    @abstractmethod
    def solve(self):
        pass