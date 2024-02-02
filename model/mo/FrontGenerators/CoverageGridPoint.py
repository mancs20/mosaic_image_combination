from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy


class CoverageGridPoint(FrontGeneratorStrategy):
    """
    This class implements coverage grid point based representation (GPBA-A) algorithm described in the paper
    'New ϵ−constraint methods for multi-objective integer linear programming: A Pareto front representation approach'
    DOI: 10.1016/j.ejor.2022.07.044
    This algorithm tries to represent all the areas of the Pareto front by minimizing the maximum distance between two
    consecutive solutions in the Pareto front.
    """
    def __init__(self, solver, timer):
        super().__init__(solver, timer)
        self.best_objective_values = None
        self.nadir_objectives_values = None
        self.check_number_of_objectives()
        self.front_solutions = []

    def solve(self):
        yield from self.get_best_worst_values()

    def get_best_worst_values(self):
        if len(self.solver.model.objectives) == 2:
            yield from self.get_best_worst_for_2obj_lexicographically()

    def get_best_worst_for_2obj_lexicographically(self):
        self.best_objective_values = [0] * len(self.solver.model.objectives)
        self.nadir_objectives_values = [0] * len(self.solver.model.objectives)
        for i in range(len(self.solver.model.objectives)):
            if i == 0:
                obj_lexicographic = self.solver.model.objectives
                j = 1
            else:
                j = 0
                obj_lexicographic = self.solver.model.objectives[i:] + self.solver.model.objectives[:i]
            self.solver.set_lexicographic_optimization(obj_lexicographic)
            self.solver.set_optimization_sense(self.model_optimization_sense)
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=True)
            formatted_solution = self.process_feasible_solution(solution_sec)
            self.front_solutions.append(formatted_solution)
            yield formatted_solution
            self.best_objective_values[i] = formatted_solution['objs'][i]
            self.nadir_objectives_values[j] = formatted_solution['objs'][j]

    def check_number_of_objectives(self):
        if len(self.solver.model.objectives) > 2:
            raise ValueError("This implementation only works for 2 objectives.")

    def always_add_new_solutions_to_front(self):
        return True
