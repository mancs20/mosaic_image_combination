import copy

from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy


class Saugmecon(FrontGeneratorStrategy):
    def __init__(self, solver, timer):
        super().__init__(solver, timer)
        self.best_objective_values = None
        self.nadir_objectives_values = None
        self.constraint_objectives = [0] * (len(self.solver.model.objectives) - 1) # all objectives except objective[0]

    def solve(self):
        formatted_solutions, self.best_objective_values, self.nadir_objectives_values = self.initialize_model_with_e_constraint()
        # check if the solver could find the optimum for each objective
        for formatted_solution in formatted_solutions:
            if formatted_solution is not None:
                yield formatted_solution
            else:
                raise TimeoutError()
        # initialize loop-control variables with values equal to the nadir values + 1
        ef_array = [self.nadir_objectives_values[i] + 1 for i in range(len(self.nadir_objectives_values))]
        rwv = copy.deepcopy(self.best_objective_values)
        previous_solutions = set()
        # add initial objective constraints
        self.add_objectives_as_constraints(ef_array)
        previous_solution_information = []
        yield from self.saugmecon_loop(ef_array, rwv, len(self.best_objective_values), previous_solution_information,
                                       previous_solutions)

    def add_objectives_as_constraints(self, ef_array):
        for i in range(len(self.constraint_objectives)):
            self.constraint_objectives[i] = self.solver.add_constraints_leq(self.solver.model.objectives[i+1], ef_array[i])

    def update_objective_constraints(self, ef_array):
        for constraint in self.constraint_objectives:
            self.solver.remove_constraints(constraint)
        self.add_objectives_as_constraints(ef_array)

    def saugmecon_loop(self, ef_array, rwv, id_objective, previous_solution_information, previous_solutions):
        id_objective -= 1
        while ef_array[id_objective] > self.best_objective_values[id_objective]:
            ef_array[id_objective] -= 1
            if id_objective == 0:
                # solve the saugmecon model
                while ef_array[id_objective] > self.best_objective_values[id_objective]:
                    ef_array[id_objective] -= 1
                    yield from self.solve_saugmecon_most_inner_loop(ef_array, rwv, previous_solution_information,
                                                                     previous_solutions)
                    
                return
            else:
                yield from self.saugmecon_loop(ef_array, rwv, id_objective, previous_solution_information, previous_solutions)
                ef_array[id_objective-1] = self.nadir_objectives_values[id_objective - 1] + 1
                if ef_array[id_objective] > self.best_objective_values[id_objective]:
                    ef_array[id_objective] = rwv[id_objective]
                    rwv[id_objective] = self.best_objective_values[id_objective]
        id_objective += 1
        return

    def solve_saugmecon_most_inner_loop(self, ef_array, rwv, previous_solution_information, previous_solutions):
        exit_from_loop_with_acceleration = False
        one_solution = []
        previous_solution_relaxation, previous_solution_values = \
            self.search_previous_solutions_relaxation(ef_array, previous_solution_information)
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
                selected_images = self.solver.model.get_solution_values()
                str_selected_images = '-'.join((str(i) for i in selected_images))
                if str_selected_images in previous_solutions:
                    one_solution = self.solver.get_solution_objective_values()
                else:
                    # update previous_solutions
                    previous_solutions.add(str_selected_images)
                    # update statistics
                    self.solver.update_statistics(solution_sec)
                    # record the solution
                    formatted_solution = self.prepare_solution()
                    one_solution = formatted_solution["objs"]
                    self.save_solution_information(ef_array, one_solution, previous_solution_information)
                    yield formatted_solution
        if exit_from_loop_with_acceleration:
            self.exit_from_loop_with_acceleration(ef_array, self.nadir_objectives_values, self.best_objective_values)
        elif len(one_solution) > 0:
            ef_array[0] = one_solution[1]  # one_solution[0] is the main objective
            self.explore_new_relatively_worst_values_of_objectives(rwv, one_solution,
                                                                         minimization=True)
        else:
            # this should not happen if the solver is working properly
            raise Exception("The solver did not find any solution")

    @staticmethod
    def exit_from_loop_with_acceleration(ef_array, nadir_objective_values, best_objective_values):
        i = 0
        while i < (len(ef_array) - 1) and ef_array[i] == nadir_objective_values[i]:
            i += 1
        for j in range(i + 1):
            ef_array[j] = best_objective_values[j]
        return ef_array

    @staticmethod
    def explore_new_relatively_worst_values_of_objectives(rwv, one_solution, minimization=True):
        # one_solution[0] is the main objective
        if minimization:
            for i in range(len(rwv)):
                if rwv[i] < one_solution[i + 1]:
                    rwv[i] = one_solution[i + 1]
        else:
            print("one_solution: ", one_solution)
            print("rwv: ", rwv)
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

    def search_previous_solutions_relaxation(self, ef_array_actual_solution, previous_solution_information):
        there_is_relaxation_for_ef_array_actual_solution = False
        if len(previous_solution_information) == 0:
            return there_is_relaxation_for_ef_array_actual_solution, None

        # find closer relaxation and check if the solution satisfy the ef_array_actual_solution
        previous_closer_relaxation = self.get_closer_relaxation(ef_array_actual_solution, previous_solution_information)
        if previous_closer_relaxation is False:
            return there_is_relaxation_for_ef_array_actual_solution, None
        else:
            f_solution_values = previous_closer_relaxation[1]
            there_is_relaxation_for_ef_array_actual_solution = True
            if type(f_solution_values) is not str:
                f_solution_values_for_constraint = f_solution_values[1:len(f_solution_values)]
                if not self.solution_satisfy_ef_arr(f_solution_values_for_constraint, ef_array_actual_solution):
                    there_is_relaxation_for_ef_array_actual_solution = False

        return there_is_relaxation_for_ef_array_actual_solution, f_solution_values

    def get_closer_relaxation(self, ef_array_actual_solution, previous_solution_information):
        idx = self.bisect_right_previous_solutions(ef_array_actual_solution, previous_solution_information)
        if idx == 0:
            return False
        return previous_solution_information[idx - 1]

    @staticmethod
    def solution_satisfy_ef_arr(solution_values, ef_arr):
        satisfy = True
        for i in range(len(ef_arr)):
            if solution_values[i] > ef_arr[i]:
                satisfy = False
                break
        return satisfy


    def initialize_model_with_e_constraint(self):
        formatted_solutions, best_constraint_objective_values = self.get_best_constraint_objective_values()
        if None in formatted_solutions:
            return formatted_solutions, best_constraint_objective_values, None
        nadir_objectives = self.get_nadir_objectives()[1:]  # in this case, the nadir is the max
        # prepare the model for the e-constraint method
        self.solver.set_optimization_sense("min")
        range_array = [abs(nadir_objectives[i] - best_constraint_objective_values[i]) for i in range(len(nadir_objectives))]
        # self.solver.optimize_e_constraint_saugmecon(range_array)
        self.optimize_e_constraint_saugmecon(range_array)
        return formatted_solutions, best_constraint_objective_values, nadir_objectives

    def optimize_e_constraint_saugmecon(self, range_array):
        self.solver.build_objective_e_constraint_saugmecon(range_array)

    def get_best_constraint_objective_values(self):
        objectives_values = [0] * len(self.constraint_objectives)
        formatted_solutions = [0] * len(self.constraint_objectives)
        # todo the sense should be given by the model, together with objective values
        sense = "min"
        for i in range(len(self.constraint_objectives)):
            formatted_solution, objective_val = self.optimize_single_objectives(sense, i+1)
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
        timeout = self.timer.resume()
        self.solver.set_time_limit(timeout.total_seconds())
        self.solver.solve(optimize_not_satisfy=True)

        solution_sec = self.timer.pause()
        print("The solver found min of objective " + str(id_objective) + " in " + str(solution_sec) + " seconds")
        if self.solver.status_time_limit():
            return None, None
        formatted_solution = self.prepare_solution()
        objective_val = formatted_solution['objs'][id_objective]
        self.solver.update_statistics(solution_sec)
        self.solver.reset()
        return formatted_solution, objective_val