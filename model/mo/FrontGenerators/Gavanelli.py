from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy


class Gavanelli(FrontGeneratorStrategy):
    def __init__(self, solver, timer):
        super().__init__(solver, timer)

    def solve(self):
        or_constraint = None
        whole_front_found = False
        id_or_constraint = 0
        while not whole_front_found:
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=False)
            if self.solver.status_infeasible():
                whole_front_found = True
            else:
                # update statistics
                self.solver.update_statistics(solution_sec)
                # record the solution
                formatted_solution = self.prepare_solution()
                one_solution = formatted_solution["objs"]
                # if or_constraint is not None:
                #     self.solver.remove_constraints(or_constraint)
                or_constraint = self.solver.add_or_all_objectives_constraint(one_solution, id_or_constraint)
                id_or_constraint += 1
                yield formatted_solution

    def add_or_constraint(self, rhs):
        return self.solver.add_or_all_objectives_constraint(rhs)
        # model.AddBoolOr([x, y.Not()])
