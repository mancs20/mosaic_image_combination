from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy


class Gavanelli(FrontGeneratorStrategy):
    def __init__(self, solver, timer, optimize=False):
        super().__init__(solver, timer)
        self.optimize = optimize

    def add_new_solutions_to_front_and_remove_dominated(self):
        return True

    def set_multiply_solution_by_minus_one(self):
        return False

    def solve(self):
        whole_front_found = False
        id_or_constraint = 0
        if self.optimize:
            self.configure_optimization()
        while not whole_front_found:
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=self.optimize)
            if self.solver.status_infeasible():
                whole_front_found = True
                formatted_solution = None
                self.solver.update_statistics(solution_sec)
            else:
                formatted_solution = self.process_feasible_solution(solution_sec)
                one_solution = formatted_solution["objs"]
                self.solver.add_or_all_objectives_constraint(one_solution, id_or_constraint)
                id_or_constraint += 1
            yield formatted_solution

    def configure_optimization(self):
        self.solver.set_single_objective(self.solver.model.objectives[0])
        self.set_maximization_or_minimization()

    def set_maximization_or_minimization(self):
        if self.solver.model.is_a_minimization_model():
            self.solver.set_minimization()
        else:
            self.solver.set_maximization()
