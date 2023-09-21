from MO import MO

from ParetoFront import ParetoFront

class MOMIP():
    """Multi-objective solver maintaining a Pareto front.
         See further information in the class `ParetoFront`.
      Args:
        instance (Instance): A constraint model.
        statistics (dict): A dictionary to store the statistics of the solver.
        front_generator: A front generator strategy with a solver supporting `solve()`.
        verbose (Bool): If `True`, the solver prints the Pareto front, new objectives and statistics at each iteration."""
    def __init__(self, instance, statistics, front_generator, verbose=True):
        # super().__init__(instance, statistics, front_generator, verbose=True)
        self.instance = instance
        self.front_generator_strategy = front_generator
        self.pareto_front = ParetoFront(instance)
        self.verbose = verbose
        self.statistics = statistics
        self.init_statistics()

    def init_statistics(self):
        self.statistics["pareto_front"] = ""
        self.statistics["solutions_pareto_front"] = ""


    def solve(self):
        for x in self.front_generator_strategy.solve():
            self.add_solution_pareto_front(x)
            self.print_statistics_of_recent_solution(x)
            yield x

    def add_solution_pareto_front(self, solution):
        self.pareto_front.join(solution)
        self.statistics["pareto_front"] = self.pareto_front.to_str()
        self.statistics["solutions_pareto_front"] = self.pareto_front.solutions_to_str()


    def print_statistics_of_recent_solution(self, solution):
        if self.verbose:
            print("New objective found: " + str(solution["objs"]))
            print(self.statistics["pareto_front"])
            print(self.pareto_front.front_constraint_mzn())
            print(solution.statistics)

    def econstraint(self):
        # TODO implement here e-constraint method
        pass