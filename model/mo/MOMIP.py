from MO import MO


class MOMIP(MO):

    def __init__(self, instance, statistics, subsolver, verbose=True):
        super().__init__(instance, statistics, subsolver, verbose=True)

    def solve(self):
        for x in self.subsolver.solve():
            self.pareto_front.join_without_pareto_verification(x)
            self.statistics["pareto_front"] = self.pareto_front.to_str()
            if self.verbose:
                print("New objective found: " + str(x["objs"]))
                print(self.statistics["pareto_front"])
                print(self.pareto_front.front_constraint_mzn())
                print(x.statistics)
            yield x
            # self.subsolver.add_local_constraint(self.pareto_front.front_constraint_mzn())

    def econstraint(self):
        # TODO implement here e-constraint method
        pass