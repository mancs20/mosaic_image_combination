from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy
from model.mo.FrontGenerators.Saugmecon import Saugmecon


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
        self.front_solutions_distance = []
        self.constraint_objectives_lhs = [0] * (len(self.solver.model.objectives) - 1)
        self.constraint_objectives = [0] * (len(self.solver.model.objectives) - 1)

    def solve(self):
        if len(self.solver.model.objectives) != 2:
            raise ValueError("This implementation only works for 2 objectives.")
        # get the best and worst values for each objective, in the case of 2 objectives, it will return the extreme
        # points of the Pareto front
        yield from self.get_best_worst_values()
        # declare the model
        self.augmecon2_model()
        # Initializes the loop control variable
        ef_array = []
        for i in range(1, len(self.nadir_objectives_values)):
            ef_array.append(self.nadir_objectives_values[i])
        # save previous solutions
        previous_solutions = set()
        previous_solution_information = []
        for solutions in self.front_solutions:
            solution_values = solutions['solution_values']
            str_solution_values = Saugmecon.convert_solution_value_to_str(solution_values)
            previous_solutions.add(str_solution_values)
        # build list with solutions sorted by second objective and write just the value of the solution, the list should be in ascending order and saved in self.front_solutions_distance
        for i in self.constraint_objectives_lhs:
            first_solutions_sorted = [self.best_objective_values[i+1], self.nadir_objectives_values[i+1]]
            self.front_solutions_distance.append(first_solutions_sorted)

        self.front_solutions.sort(key=lambda x: x['objs'][1])
        yield from self.coverage_loop(ef_array, previous_solutions, previous_solution_information)

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

    def augmecon2_model(self):
        self.constraint_objectives_lhs = self.solver.build_objective_e_constraint_augmecon2(self.nadir_objectives_values, True)
        self.solver.set_optimization_sense(self.model_optimization_sense)

    def coverage_loop(self, ef_array, previous_solutions, previous_solution_information):
        while ef_array[0] > self.best_objective_values[0]:
            yield from self.coverage_most_inner_loop(ef_array, previous_solutions, previous_solution_information)

    def coverage_most_inner_loop(self, ef_array, previous_solutions, previous_solution_information):
        exit_from_loop_with_acceleration = False
        one_solution = []
        previous_solution_relaxation, previous_solution_values = \
            Saugmecon.search_previous_solutions_relaxation(ef_array, previous_solution_information)
        if previous_solution_relaxation:
            if type(previous_solution_values) is str:
                # the previous solution is infeasible
                # todo adjust ef_array and do the loop again
                exit_from_loop_with_acceleration = True
            else:
                one_solution = previous_solution_values
        else:
            # solve the problem
            # todo copy the other part of solve_saugmecon_most_inner_loop
            # update right-hand side values (rhs) for the objective constraints
            self.update_objective_constraints(ef_array)
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=True)
            if self.solver.status_infeasible():
                Saugmecon.save_solution_information(ef_array, "infeasible", previous_solution_information)
                exit_from_loop_with_acceleration = True
            else:
                solution_values = self.solver.model.get_solution_values()
                str_solution_values = self.convert_solution_value_to_str(solution_values)
                if str_solution_values in previous_solutions:
                    one_solution = self.solver.get_solution_objective_values()
                else:
                    # update previous_solutions
                    previous_solutions.add(str_solution_values)
                    formatted_solution = self.process_feasible_solution(solution_sec)
                    one_solution = formatted_solution["objs"]
                    Saugmecon.save_solution_information(ef_array, one_solution, previous_solution_information)
                    # the line below is for testing purposes, uncomment when necessary
                    # self.solver.model.assert_solution(one_solution, formatted_solution["solution_values"])
                    yield formatted_solution
        if exit_from_loop_with_acceleration:
            self.exit_from_loop_with_acceleration(ef_array, self.nadir_objectives_values, self.best_objective_values)
        elif len(one_solution) > 0:
            ef_array[0] = one_solution[1]  # one_solution[0] is the main objective
            self.explore_new_relatively_worst_values_of_objectives(rwv, one_solution)
        else:
            # this should not happen if the solver is working properly
            raise Exception("The solver did not find any solution")

    def update_objective_constraints(self, ef_array):
        self.update_objective_constraints_coverage(ef_array)

    def update_objective_constraints_coverage(self, ef_array):
        # set ef_array[0] as the middle point between the most distant consecutive solutions in self.
        # front_solutions_distance
        # get the most distant consecutive solutions in self.front_solutions_distance
        for i in range(len(ef_array)):
            max_distance_index = self.get_most_distant_consecutive_solutions_index(i)
            ef_array[i] = (self.front_solutions_distance[i][max_distance_index] +
                           self.front_solutions_distance[i][max_distance_index + 1]) / 2
            # update the objective constraints
            if self.constraint_objectives[i] != 0:
                self.solver.remove_constraints(self.constraint_objectives[i])
            self.constraint_objectives[i] = self.solver.add_constraints_eq(self.constraint_objectives_lhs, ef_array[i])


    def get_most_distant_consecutive_solutions_index(self, dimension_id):
        max_distance = 0
        max_distance_index = 0
        for i in range(len(self.front_solutions_distance[dimension_id]) - 1):
            distance = abs(self.front_solutions_distance[dimension_id][i + 1] - self.front_solutions_distance[dimension_id][i])
            if distance > max_distance:
                max_distance = distance
                max_distance_index = i
        return max_distance_index


    def check_number_of_objectives(self):
        if len(self.solver.model.objectives) > 2:
            raise ValueError("This implementation only works for 2 objectives.")

    def always_add_new_solutions_to_front(self):
        return True
