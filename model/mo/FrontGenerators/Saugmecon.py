import copy

from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy
import numpy as np


class Saugmecon(FrontGeneratorStrategy):
    def __init__(self, solver, timer):
        super().__init__(solver, timer)
        self.best_objective_values = None
        self.nadir_objectives_values = None
        self.constraint_objectives = [0] * (len(self.solver.model.objectives) - 1) # all objectives except objective[0]

    def always_add_new_solutions_to_front(self):
        if self.not_evaluate_always_add_new_solutions_to_front:
            return False
        else:
            return self.solver.model.is_numerically_possible_augment_objective()

    def solve(self):
        formatted_solutions, self.best_objective_values, self.nadir_objectives_values = self.initialize_model_with_e_constraint()
        # check if the solver could find the optimum for each objective
        # The solutions obtained by optimizing only one objective are not necessarily on the Pareto front, they are added just in case they are.
        self.not_evaluate_always_add_new_solutions_to_front = True
        for formatted_solution in formatted_solutions:
            if formatted_solution is not None:
                yield formatted_solution
            else:
                raise TimeoutError()
        self.not_evaluate_always_add_new_solutions_to_front = False
        # initialize loop-control variables with values equal to the nadir values + 1
        ef_array = [self.nadir_objectives_values[i] - self.step for i in range(len(self.nadir_objectives_values))]
        rwv = copy.deepcopy(self.best_objective_values)
        # previous solution information
        previous_solutions = set()
        previous_solution_information = []
        for i in range(len(formatted_solutions)):
            solution_values = formatted_solutions[i]['solution_values']
            str_solution_values = self.convert_solution_value_to_str(solution_values)
            previous_solutions.add(str_solution_values)
        # add initial objective constraints
        self.add_objectives_as_constraints(ef_array)
        yield from self.saugmecon_loop(ef_array, rwv, len(self.best_objective_values), previous_solution_information,
                                       previous_solutions)

    def add_objectives_as_constraints(self, ef_array):
        for i in range(len(self.constraint_objectives)):
            if self.model_optimization_sense == "min":
                self.constraint_objectives[i] = self.solver.add_constraints_leq(self.solver.model.objectives[i+1], ef_array[i])
            else:
                self.constraint_objectives[i] = self.solver.add_constraints_geq(self.solver.model.objectives[i+1], ef_array[i])

    def update_objective_constraints(self, ef_array):
        for constraint in self.constraint_objectives:
            self.solver.remove_constraints(constraint)
        self.add_objectives_as_constraints(ef_array)

    def saugmecon_loop(self, ef_array, rwv, id_objective, previous_solution_information, previous_solutions):
        id_objective -= 1
        # while ef_array[id_objective] > self.best_objective_values[id_objective]:
        # multiply for -1 to change the sense of the comparison in case is a minimization problem
        while np.sign(self.step) * (self.best_objective_values[id_objective] - ef_array[id_objective]) > 0:
            if id_objective == 0:
                # solve the saugmecon model
                while np.sign(self.step) * (self.best_objective_values[id_objective] - ef_array[id_objective]) > 0:
                    ef_array[id_objective] += self.step
                    yield from self.solve_saugmecon_most_inner_loop(ef_array, rwv, previous_solution_information,
                                                                     previous_solutions)
                return
            else:
                ef_array[id_objective] += self.step
                yield from self.saugmecon_loop(ef_array, rwv, id_objective, previous_solution_information, previous_solutions)
                ef_array[id_objective-1] = self.nadir_objectives_values[id_objective - 1] - self.step
                if np.sign(self.step) * (self.best_objective_values[id_objective] - ef_array[id_objective]) > 0:
                    ef_array[id_objective] = rwv[id_objective]
                    rwv[id_objective] = self.best_objective_values[id_objective]
        id_objective += 1
        return

    def solve_saugmecon_most_inner_loop(self, ef_array, rwv, previous_solution_information, previous_solutions):
        exit_from_loop_with_acceleration = False
        one_solution = []
        previous_solution_relaxation, previous_solution_values = \
            Saugmecon.search_previous_solutions_relaxation(ef_array, previous_solution_information)
        if previous_solution_relaxation:
            if type(previous_solution_values) is str:
                # the previous solution is infeasible
                exit_from_loop_with_acceleration = True
            else:
                one_solution = previous_solution_values
        else:
            # update right-hand side values (rhs) for the objective constraints
            self.update_objective_constraints(ef_array)
            solution_sec =self.get_solver_solution_for_timeout(optimize_not_satisfy=True)
            if self.solver.status_infeasible():
                self.save_solution_information(ef_array, "infeasible",previous_solution_information)
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
                    self.save_solution_information(ef_array, one_solution, previous_solution_information)
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

    @staticmethod
    def convert_solution_value_to_str(solution_values):
        str_solution_values = '-'.join((str(i) for i in solution_values))
        return str_solution_values

    @staticmethod
    def exit_from_loop_with_acceleration(ef_array, nadir_objective_values, best_objective_values):
        i = 0
        while i < (len(ef_array) - 1) and ef_array[i] == nadir_objective_values[i]:
            i += 1
        for j in range(i + 1):
            ef_array[j] = best_objective_values[j]
        return ef_array

    def explore_new_relatively_worst_values_of_objectives(self, rwv, one_solution):
        if self.model_optimization_sense == "min":
            for i in range(len(rwv)):
                if one_solution[i + 1] > rwv[i]:
                    rwv[i] = one_solution[i + 1]
        else:
            for i in range(len(rwv)):
                if one_solution[i + 1] < rwv[i]:
                    rwv[i] = one_solution[i + 1]
        return rwv

    @staticmethod
    def save_solution_information(ef_array, solution, previous_solution_information):
        ef_array_to_insert = ef_array.copy()
        # insert the new solution in the correct position
        lo = Saugmecon.id_insort_right_previous_solutions(ef_array_to_insert, previous_solution_information)
        previous_solution_information.insert(lo, [ef_array_to_insert, solution])
        return previous_solution_information

    @staticmethod
    def id_insort_right_previous_solutions(ef_array, previous_solution_information):
        lo = Saugmecon.bisect_right_previous_solutions(ef_array, previous_solution_information)
        return lo

    @staticmethod
    def bisect_right_previous_solutions(ef_array, previous_solution_information):
        lo = 0
        hi = len(previous_solution_information)
        while lo < hi:
            mid = (lo + hi) // 2
            if ef_array > previous_solution_information[mid][0]:
                hi = mid
            else:
                lo = mid + 1
        return lo

    @staticmethod
    def get_less_constrained_previous_solutions(ef_array, previous_solution_information):
        if len(previous_solution_information) == 0:
            return -1
        # get position to start searching
        idx = Saugmecon.bisect_right_previous_solutions(ef_array, previous_solution_information) - 1
        solution_with_more_relaxation_found = False
        while not solution_with_more_relaxation_found and idx > -1:
            if Saugmecon.ef_array1_less_constraint_ef_array2(previous_solution_information[idx][0], ef_array, min_sense=True):
                f_solution_values = previous_solution_information[idx][1]
                # check if the solution is not infeasible. If it is infeasible return True and in the loop call Exit with
                # acceleration
                solution_with_more_relaxation_found = True
                if type(f_solution_values) is not str:
                    f_solution_values_for_constraint = f_solution_values[1:len(f_solution_values)]
                    if not Saugmecon.solution_satisfy_ef_arr(f_solution_values_for_constraint, ef_array):
                        solution_with_more_relaxation_found = False
                        idx -= 1
            else:
                idx -= 1
        return idx


    @staticmethod
    def ef_array1_less_constraint_ef_array2(ef_array1, ef_array2, min_sense=True):
        less_constraint = True
        for i in range(len(ef_array1)):
            if min_sense:
                if ef_array1[i] < ef_array2[i]:
                    less_constraint = False
                    break
            else:
                if ef_array1[i] > ef_array2[i]:
                    less_constraint = False
                    break
        return less_constraint

    @staticmethod
    def search_previous_solutions_relaxation(ef_array_actual_solution, previous_solution_information):
        # is there a previous problem with less tighten constraint ef_array_actual_solution
        # find closer relaxation and check if the solution satisfy the ef_array_actual_solution
        previous_closer_relaxation = Saugmecon.get_closer_relaxation(ef_array_actual_solution, previous_solution_information)
        if previous_closer_relaxation is False:
            return False, None
        else:
            f_solution_values = previous_closer_relaxation[1]
            return True, f_solution_values

    @staticmethod
    def get_closer_relaxation(ef_array_actual_solution, previous_solution_information):
        idx = Saugmecon.get_less_constrained_previous_solutions(ef_array_actual_solution, previous_solution_information)
        if idx < 0:
            return False
        return previous_solution_information[idx]

    @staticmethod
    def solution_satisfy_ef_arr(solution_values, ef_arr):
        i = 0
        while i < len(ef_arr) and solution_values[i] <= ef_arr[i]:
            i += 1
        return i == len(ef_arr)

    def initialize_model_with_e_constraint(self):
        formatted_solutions, best_constraint_objective_values = self.get_best_constraint_objective_values()
        if None in formatted_solutions:
            return formatted_solutions, best_constraint_objective_values, None
        nadir_objectives = self.get_nadir_objectives()[1:]  # in this case, the nadir is the max
        # prepare the model for the e-constraint method
        range_array = [abs(nadir_objectives[i] - best_constraint_objective_values[i]) for i in range(len(nadir_objectives))]
        self.optimize_e_constraint_saugmecon(range_array)
        return formatted_solutions, best_constraint_objective_values, nadir_objectives

    def optimize_e_constraint_saugmecon(self, range_array):
        self.solver.build_objective_e_constraint_saugmecon(range_array, self.always_add_new_solutions_to_front())
        self.solver.set_optimization_sense(self.model_optimization_sense)

    def get_best_constraint_objective_values(self):
        objectives_values = [0] * len(self.constraint_objectives)
        formatted_solutions = [0] * len(self.constraint_objectives)
        for i in range(len(self.constraint_objectives)):
            formatted_solution, objective_val = self.optimize_single_objectives(self.model_optimization_sense, i+1)
            objectives_values[i] = objective_val
            formatted_solutions[i] = formatted_solution
            if formatted_solution is None:
                 break
        return formatted_solutions, objectives_values

    def get_nadir_objectives(self):
        nadir_objectives = self.solver.model.get_nadir_bound_estimation()
        return nadir_objectives

    def optimize_single_objectives(self, sense, id_objective):
        objective = self.solver.model.objectives[id_objective]
        print("Start the solver to get the min of objective " + str(id_objective))
        self.solver.set_single_objective(objective)
        self.solver.set_optimization_sense(sense)
        solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=True)
        print("The solver found min of objective " + str(id_objective) + " in " + str(solution_sec) + " seconds")
        formatted_solution = self.process_feasible_solution(solution_sec)
        objective_val = formatted_solution['objs'][id_objective]
        self.solver.reset()
        return formatted_solution, objective_val

    def test_if_solver_produce_solutions(self, solutions):
        all_solutions_found = True
        constraint_objectives_values = [0] * len(solutions[0])
        # constraint_objectives_values = []
        for i in range(len(solutions)):
            solution_to_test = solutions[i]
            if i > 0:
                for constraint in constraint_objectives_values:
                    self.solver.remove_constraints(constraint)
            for j in range(len(solution_to_test)):
                constraint = self.solver.add_constraints_eq(self.solver.model.objectives[j], solution_to_test[j])
                constraint_objectives_values[j] = constraint
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=True)
            if self.solver.status_infeasible():
                print(f"The solver found infeasible solution for objectives values {solution_to_test} so solution {solution_to_test} cannot be obtained with the solver")
                all_solutions_found = False
            else:
                formatted_solution = self.prepare_solution()
                solution_values = formatted_solution['objs']
                if solution_values != solution_to_test:
                    print(f"The solver found solution {solution_values} but the expected solution is {solution_to_test}")
                    all_solutions_found = False
                else:
                    print(f"The solver found solution {solution_values} as expected")
        if all_solutions_found:
            print("All solutions were found by the solver")
        return all_solutions_found