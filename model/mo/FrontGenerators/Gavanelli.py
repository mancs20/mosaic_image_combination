from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy


class Gavanelli(FrontGeneratorStrategy):
    def __init__(self, solver, timer):
        super().__init__(solver, timer)

    def always_add_new_solutions_to_front(self):
        return True

    def solve(self):
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
                self.solver.add_or_all_objectives_constraint(one_solution, id_or_constraint)
                id_or_constraint += 1
                yield formatted_solution