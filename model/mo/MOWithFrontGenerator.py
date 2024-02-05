from ParetoFront import ParetoFront


class MOWithFrontGenerator:
    """Multi-objective solver maintaining a Pareto front.
         See further information in the class `ParetoFront`.
      Args:
        instance (Instance): An instance class for a particular problem.
        statistics (dict): A dictionary to store the statistics of the solver.
        front_generator: A front generator strategy with a solver supporting `solve()`.
        verbose (Bool): If `True`, the solver prints the Pareto front, new objectives and statistics at each iteration."""

    def __init__(self, instance, statistics, front_generator, verbose=True):
        self.instance = instance
        self.front_generator_strategy = front_generator
        self.pareto_front = ParetoFront()
        self.verbose = verbose
        self.statistics = statistics
        self.init_statistics()

    def init_statistics(self):
        self.statistics["pareto_front"] = ""
        self.statistics["solutions_pareto_front"] = ""
        self.statistics["hypervolume_current_solutions"] = []

    def solve(self):
        for x in self.front_generator_strategy.solve():
            self.add_solution_pareto_front(x)
            self.print_statistics_of_recent_solution(x)
            yield x

    def add_solution_pareto_front(self, solution, added_to_front_verification=True):
        added_to_front = self.pareto_front.join(solution)
        error = False
        error_msg = (f"Error!! solution {solution} is a new solution which is dominated by some of the previous. "
                     f"Previous solutions: {self.pareto_front.solutions}")
        if added_to_front_verification and not added_to_front and self.front_generator_strategy.always_add_new_solutions_to_front():
            error = True
            print(f"Error!! solution {solution} is a new solution which is dominated by some of the previous")
            print(f"Previous solutions: {self.pareto_front.solutions}")
        if added_to_front:
            self.statistics["pareto_front"] = self.pareto_front.to_str()
            self.statistics["solutions_pareto_front"] = self.pareto_front.solutions_to_str()
            # create list from string
            self.statistics["hypervolume_current_solutions"].append(self.pareto_front.hypervolume())
        if error:
            raise Exception(error_msg)
        return added_to_front

    def print_statistics_of_recent_solution(self, solution):
        if self.verbose:
            print("New objective found: " + str(solution["objs"]))
            print(self.statistics["pareto_front"])
            print(self.pareto_front.front_constraint_mzn())  # todo this print is only usefull in Gavenelli, remove it
            print(solution.statistics)

    def process_last_incomplete_solution(self):
        added_to_front = False
        if self.front_generator_strategy.solution_incomplete_due_timeout is not None:
            added_to_front = self.add_solution_pareto_front(
                self.front_generator_strategy.solution_incomplete_due_timeout, added_to_front_verification=False)
        return added_to_front
