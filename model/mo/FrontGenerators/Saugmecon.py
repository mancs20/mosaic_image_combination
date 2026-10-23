import copy

from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy
from model.mo.FrontGenerators.SaugmeconAugmentation import compute_saugmecon_augmentation, DEFAULT_GUARD
import numpy as np


class Saugmecon(FrontGeneratorStrategy):
    def __init__(self, solver, timer, guard=DEFAULT_GUARD):
        super().__init__(solver, timer)
        self.guard = guard
        self.constraint_objectives = [0] * (len(self.solver.model.objectives) - 1)  # all objectives except objective[0]
        # True when the objective is augmented: the solutions returned are Pareto optimal
        self.augmentation_active = False

    def set_multiply_solution_by_minus_one(self):
        return False

    def add_new_solutions_to_front_and_remove_dominated(self):
        # Saugmecon never aborts because of a dominated solution, see add_new_solutions_without_dominance_check
        return False

    def add_new_solutions_without_dominance_check(self):
        # with the augmented objective the solver returns Pareto optimal solutions. The solutions of the single
        # objectives are not added this way: they are not necessarily Pareto optimal, the front compares them
        return self.augmentation_active and not self.new_solutions_require_dominance_check

    def solve(self):
        formatted_solutions, self.best_objective_values, self.nadir_objectives_values = (
            self.initialize_model_with_e_constraint())
        # check if the solver could find the optimum for each objective
        # The solutions obtained by optimizing only one objective are not necessarily on the Pareto front,
        # they are added just in case they are.
        self.new_solutions_require_dominance_check = True
        for formatted_solution in formatted_solutions:
            if formatted_solution is not None:
                yield formatted_solution
            else:
                raise TimeoutError()
        self.new_solutions_require_dominance_check = False
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
                self.constraint_objectives[i] = self.solver.add_constraints_leq(self.solver.model.objectives[i+1],
                                                                                ef_array[i])
            else:
                self.constraint_objectives[i] = self.solver.add_constraints_geq(self.solver.model.objectives[i+1],
                                                                                ef_array[i])

    def update_objective_constraints(self, ef_array):
        for constraint in self.constraint_objectives:
            self.solver.remove_constraint(constraint)
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
                yield from self.saugmecon_loop(ef_array, rwv, id_objective, previous_solution_information,
                                               previous_solutions)
                ef_array[id_objective-1] = self.nadir_objectives_values[id_objective - 1] - self.step
                if np.sign(self.step) * (self.best_objective_values[id_objective] - ef_array[id_objective]) > 0:
                    ef_array[id_objective] = rwv[id_objective]
                    rwv[id_objective] = self.best_objective_values[id_objective]
        id_objective += 1
        return

    def solve_saugmecon_most_inner_loop(self, ef_array, rwv, previous_solution_information, previous_solutions):
        exit_from_loop_with_acceleration = False
        one_solution = []
        # the search and the insertion in previous_solution_information depend on the optimization sense
        min_sense = self.model_optimization_sense == "min"
        previous_solution_relaxation, previous_solution_values = \
            Saugmecon.search_previous_solutions_relaxation(ef_array, previous_solution_information, min_sense)
        if previous_solution_relaxation:
            if type(previous_solution_values) is str:
                # the previous solution is infeasible
                exit_from_loop_with_acceleration = True
            else:
                one_solution = previous_solution_values
        else:
            # update right-hand side values (rhs) for the objective constraints
            self.update_objective_constraints(ef_array)
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=True)
            if self.solver.status_infeasible():
                self.save_solution_information(ef_array, "infeasible", previous_solution_information, min_sense)
                exit_from_loop_with_acceleration = True
                formatted_solution = None
                self.solver.update_statistics(solution_sec)
            else:
                solution_values = self.solver.model.get_solution_values()
                str_solution_values = self.convert_solution_value_to_str(solution_values)
                formatted_solution = self.process_feasible_solution(solution_sec)
                if str_solution_values in previous_solutions:
                    one_solution = self.solver.get_solution_objective_values()
                else:
                    # update previous_solutions
                    previous_solutions.add(str_solution_values)
                    one_solution = formatted_solution["objs"]
                    # the line below is for testing purposes, uncomment when necessary
                    # self.solver.model.assert_solution(one_solution, formatted_solution["solution_values"])
                # saved also when the solution was found before (as in Choco), so the next e-constraint problems
                # it satisfies are not solved again
                self.save_solution_information(ef_array, one_solution, previous_solution_information, min_sense)
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
    def save_solution_information(ef_array, solution, previous_solution_information, min_sense=True):
        ef_array_to_insert = ef_array.copy()
        # insert the new solution in the correct position
        if min_sense:
            lo = Saugmecon.id_insort_right_previous_solutions(ef_array_to_insert, previous_solution_information)
        else:
            lo = Saugmecon.id_insort_left_previous_solutions(ef_array_to_insert, previous_solution_information)
        previous_solution_information.insert(lo, [ef_array_to_insert, solution])
        return previous_solution_information

    @staticmethod
    def id_insort_right_previous_solutions(ef_array, previous_solution_information):
        lo = Saugmecon.bisect_right_previous_solutions_sorted_descending(ef_array, previous_solution_information)
        return lo

    @staticmethod
    def bisect_right_previous_solutions_sorted_descending(ef_array, previous_solution_information):
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
    def id_insort_left_previous_solutions(ef_array, previous_solution_information):
        lo = Saugmecon.bisect_left_previous_solutions_sorted_descending(ef_array, previous_solution_information)
        return lo

    @staticmethod
    def bisect_left_previous_solutions_sorted_descending(ef_array, previous_solution_information):
        lo = 0
        hi = len(previous_solution_information)
        while lo < hi:
            mid = (lo + hi) // 2
            if ef_array < previous_solution_information[mid][0]:
                hi = mid
            else:
                lo = mid + 1
        return lo

    @staticmethod
    def get_less_constrained_previous_solutions(ef_array, previous_solution_information, min_sense=True):
        if len(previous_solution_information) == 0:
            return -1
        # get position to start searching
        if min_sense:
            idx = (Saugmecon.bisect_right_previous_solutions_sorted_descending(ef_array, previous_solution_information)
                   - 1)
        else:
            idx = (Saugmecon.bisect_left_previous_solutions_sorted_descending(ef_array, previous_solution_information)
                   - 1)
        solution_with_more_relaxation_found = False
        while not solution_with_more_relaxation_found and idx > -1:
            if Saugmecon.ef_array1_less_constraint_ef_array2(previous_solution_information[idx][0], ef_array,
                                                             min_sense=min_sense):
                f_solution_values = previous_solution_information[idx][1]
                # check if the solution is not infeasible. If it is infeasible return True and in the loop call Exit
                # with acceleration
                solution_with_more_relaxation_found = True
                if type(f_solution_values) is not str:
                    f_solution_values_for_constraint = f_solution_values[1:len(f_solution_values)]
                    if not Saugmecon.solution_satisfy_ef_arr(f_solution_values_for_constraint, ef_array,
                                                             min_sense=min_sense):
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
    def search_previous_solutions_relaxation(ef_array_actual_solution, previous_solution_information, min_sense=True):
        # is there a previous problem with less tighten constraint ef_array_actual_solution
        # find closer relaxation and check if the solution satisfy the ef_array_actual_solution
        previous_closer_relaxation = Saugmecon.get_closer_relaxation(ef_array_actual_solution,
                                                                     previous_solution_information, min_sense=min_sense)
        if previous_closer_relaxation is False:
            return False, None
        else:
            f_solution_values = previous_closer_relaxation[1]
            return True, f_solution_values

    @staticmethod
    def get_closer_relaxation(ef_array_actual_solution, previous_solution_information, min_sense=True):
        idx = Saugmecon.get_less_constrained_previous_solutions(ef_array_actual_solution, previous_solution_information,
                                                                min_sense=min_sense)
        if idx < 0:
            return False
        return previous_solution_information[idx]

    @staticmethod
    def solution_satisfy_ef_arr(solution_values, ef_arr, min_sense=True):
        i = 0
        sense_sign = -1 if min_sense else 1
        while i < len(ef_arr) and (sense_sign*(ef_arr[i] - solution_values[i]) <= 0):
            i += 1
        return i == len(ef_arr)

    def initialize_model_with_e_constraint(self):
        # the best value of each objective must be exact, ask the solver to tell apart differences of 1
        self.solver.configure_objective_resolution(1)
        formatted_solutions, best_constraint_objective_values = self.get_best_constraint_objective_values()
        if None in formatted_solutions:
            return formatted_solutions, best_constraint_objective_values, None
        nadir_objectives = self.get_nadir_objectives()[1:]  # in this case, the nadir is the max
        # prepare the model for the e-constraint method
        range_array = [abs(nadir_objectives[i] - best_constraint_objective_values[i]) for i in
                       range(len(nadir_objectives))]
        self.optimize_e_constraint_saugmecon(range_array)
        return formatted_solutions, best_constraint_objective_values, nadir_objectives

    def optimize_e_constraint_saugmecon(self, range_array):
        augmentation = self.solver.model.is_numerically_possible_augment_objective()
        if augmentation and self.solver.supports_real_valued_objective():
            self.build_augmented_objective(range_array)
        else:
            # CP solvers: integer objective built by the solver
            self.solver.build_objective_e_constraint_saugmecon(range_array, augmentation)
        # with the augmented objective the solver returns Pareto optimal solutions, so the front adds the new ones
        # without comparing them with the rest of the front
        self.augmentation_active = augmentation
        self.solver.set_optimization_sense(self.model_optimization_sense)

    def build_augmented_objective(self, range_array):
        # objective = f_0 + delta * sum(f_i / r_i), see SaugmeconAugmentation
        augmentation = compute_saugmecon_augmentation(range_array, self.guard)
        self.solver.configure_objective_resolution(augmentation.min_difference)
        self.solver.build_objective_with_delta(augmentation.delta, range_array)
        print(f"Saugmecon augmented objective: delta {augmentation.delta}, guard {augmentation.guard}, smallest "
              f"difference {augmentation.min_difference}")

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

    def test_if_solver_produce_solutions(self, solutions):
        all_solutions_found = True
        constraint_objectives_values = [0] * len(solutions[0])
        # constraint_objectives_values = []
        for i in range(len(solutions)):
            solution_to_test = solutions[i]
            if i > 0:
                for constraint in constraint_objectives_values:
                    self.solver.remove_constraint(constraint)
            for j in range(len(solution_to_test)):
                constraint = self.solver.add_constraints_eq(self.solver.model.objectives[j], solution_to_test[j])
                constraint_objectives_values[j] = constraint
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=True)
            if self.solver.status_infeasible():
                print(f"The solver found infeasible solution for objectives values {solution_to_test} so solution "
                      f"{solution_to_test} cannot be obtained with the solver")
                all_solutions_found = False
            else:
                formatted_solution = self.prepare_solution()
                solution_values = formatted_solution['objs']
                if solution_values != solution_to_test:
                    print(f"The solver found solution {solution_values} but the expected solution is "
                          f"{solution_to_test}")
                    all_solutions_found = False
                else:
                    print(f"The solver found solution {solution_values} as expected")
        if all_solutions_found:
            print("All solutions were found by the solver")
        return all_solutions_found
