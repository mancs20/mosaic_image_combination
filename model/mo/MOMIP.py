from MO import MO


class MOMIP(MO):

    def __init__(self, instance, statistics, subsolver, verbose=True):
        super().__init__(instance, statistics, subsolver, verbose=True)

    def solve(self):
        for x in self.subsolver.solve():
            self.add_solution_pareto_front(x)
            self.print_statistics_of_recent_solution(x)
            yield x

    def add_solution_pareto_front(self, solution):
        self.pareto_front.join(solution)
        self.statistics["pareto_front"] = self.pareto_front.to_str()
        self.statistics["solutions_pareto_front"] = self.pareto_front.solutions_to_str()
        self.statistics["ef_array"] = self.pareto_front.ef_arr_to_str()

    def print_statistics_of_recent_solution(self, solution):
        if self.verbose:
            print("New objective found: " + str(solution["objs"]))
            print(self.statistics["pareto_front"])
            print(self.pareto_front.front_constraint_mzn())
            print(solution.statistics)

    def econstraint(self):
        # TODO implement here e-constraint method
        pass