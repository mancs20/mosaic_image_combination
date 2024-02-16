import numpy as np

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
        self.constraint_objectives_lhs = None
        self.constraint_objectives = [0] * (len(self.solver.model.objectives) - 1)
        self.is_a_minimization_model_originally = False

    def solve(self):
        # get the best and worst values for each objective, in the case of 2 objectives, it will return the extreme
        # points of the Pareto front
        yield from self.get_best_worst_values()
        # convert problem to maximization problem
        self.convert_model_to_maximization()
        # declare the model
        self.set_augmecon2_objective_model()
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
        min_interval = min(self.nadir_objectives_values[1], self.best_objective_values[1])
        max_interval = max(self.nadir_objectives_values[1], self.best_objective_values[1])
        ef_interval = IntervalManager(min_interval+1, max_interval-1)

        if len(self.solver.model.objectives) == 2:
            ef_array[0] = int((self.best_objective_values[1] + self.nadir_objectives_values[1]) / 2)
        yield from self.coverage_loop(ef_array, previous_solutions, previous_solution_information, ef_interval)

    def coverage_loop(self, ef_array, previous_solutions, previous_solution_information, ef_interval):
        while ef_array[0] <= self.best_objective_values[1]:
            yield from self.coverage_most_inner_loop(ef_array, previous_solutions, previous_solution_information,
                                                     ef_interval)

    def coverage_most_inner_loop(self, ef_array, previous_solutions, previous_solution_information, ef_interval):
        gamma = 1  # with the value of 1, the algorithm will find the whole Pareto front if run enough time
        previous_solution_relaxation, previous_solution_values = \
            Saugmecon.search_previous_solutions_relaxation(ef_array, previous_solution_information, min_sense=False)
        if previous_solution_relaxation:
            if type(previous_solution_values) is str:
                # the previous solution is infeasible
                one_solution = []
            else:
                one_solution = previous_solution_values
        else:
            # solve the problem
            # update right-hand side values (rhs) for the objective constraints
            self.update_objective_constraints(ef_array)
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=True)
            if self.solver.status_infeasible():
                Saugmecon.save_solution_information(ef_array, "infeasible", previous_solution_information,
                                                    min_sense=False)
                one_solution = []
            else:
                solution_values = self.solver.model.get_solution_values()
                str_solution_values = Saugmecon.convert_solution_value_to_str(solution_values)
                if str_solution_values in previous_solutions:
                    one_solution = self.solver.get_solution_objective_values()
                else:
                    # update previous_solutions
                    previous_solutions.add(str_solution_values)
                    formatted_solution = self.process_feasible_solution(solution_sec)
                    one_solution = formatted_solution["objs"]
                    Saugmecon.save_solution_information(ef_array, one_solution, previous_solution_information,
                                                        min_sense=False)
                    # the line below is for testing purposes, uncomment when necessary
                    # self.solver.model.assert_solution(one_solution, formatted_solution["solution_values"])
                    if self.is_a_minimization_model_originally:
                        formatted_solution.solution.objs = [-1 * i for i in formatted_solution.solution.objs]
                    yield formatted_solution
        for i in range(len(self.constraint_objectives)):
            self.adjust_parameter_ef_array(gamma, i, ef_array, one_solution, ef_interval)

    def adjust_parameter_ef_array(self, gamma, id_constraint_objective, ef_array, one_solution, ef_interval):
        # check if the list one_solution is empty
        start_removal = ef_array[id_constraint_objective]
        new_max_interval = start_removal - 1
        if not one_solution:
            end_removal = ef_interval.max_value
        else:
            end_removal = min(one_solution[id_constraint_objective + 1], ef_interval.max_value)
        ef_interval.remove_interval(start_removal, end_removal)
        # update max_value
        if end_removal >= ef_interval.max_value:
            ef_interval.max_value = new_max_interval
        max_interval = ef_interval.find_largest_interval()
        if max_interval is not None:
            ef_array[id_constraint_objective] = int((max_interval[0] + max_interval[1]) / 2)
        else:
            ef_array[id_constraint_objective] = self.best_objective_values[id_constraint_objective + 1] + 1

    def convert_model_to_maximization(self):
        if not self.solver.model.is_a_minimization_model():
            return  # the model is already a maximization model
        self.is_a_minimization_model_originally = True
        # multiply nadir and best values by -1
        self.best_objective_values = [-1 * x for x in self.best_objective_values]
        self.nadir_objectives_values = [-1 * x for x in self.nadir_objectives_values]
        # multiply objectives by -1
        for i in range(len(self.solver.model.objectives)):
            self.solver.change_objective_sense(i)

    def get_best_worst_values(self):
        if len(self.solver.model.objectives) == 2:
            yield from self.get_best_worst_for_2obj_lexicographically()

    def get_best_worst_for_2obj_lexicographically(self):
        self.best_objective_values = [0] * len(self.solver.model.objectives)
        self.nadir_objectives_values = [0] * len(self.solver.model.objectives)
        for i in range(len(self.solver.model.objectives)):
            if i == 0:
                obj_lexicographic = [0, 1]
                j = 1
            else:
                j = 0
                obj_lexicographic = [1, 0]
            self.solver.set_lexicographic_optimization(obj_lexicographic)
            self.solver.set_optimization_sense(self.model_optimization_sense)
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=True)
            formatted_solution = self.process_feasible_solution(solution_sec)
            self.front_solutions.append(formatted_solution)
            yield formatted_solution
            self.best_objective_values[i] = formatted_solution['objs'][i]
            self.nadir_objectives_values[j] = formatted_solution['objs'][j]
        self.solver.lexicographic_obj_order = []

    def set_augmecon2_objective_model(self):
        self.constraint_objectives_lhs = self.solver.build_objective_e_constraint_augmecon2(
            self.best_objective_values, self.nadir_objectives_values, True)
        self.solver.set_optimization_sense("max")

    def update_objective_constraints(self, ef_array):
        for i in range(len(ef_array)):
            # todo uncomment below
            if self.constraint_objectives[i] != 0:
                self.solver.remove_constraints(self.constraint_objectives[i])
            self.constraint_objectives[i] = self.solver.add_constraints_eq(self.constraint_objectives_lhs[i],
                                                                           ef_array[i])

    def check_number_of_objectives(self):
        if len(self.solver.model.objectives) > 2:
            raise ValueError("This implementation only works for 2 objectives.")

    def always_add_new_solutions_to_front(self):
        return True


class IntervalManager:
    def __init__(self, min_value, max_value):
        self.intervals = set()  # Using set to manage unique intervals
        self.min_value = min_value
        self.max_value = max_value
        self.add_interval(min_value, max_value)

    def add_interval(self, start, end):
        """
        Adds a new interval, merging with existing ones if overlapping.
        """
        new_intervals = set()
        to_add = (start, end)
        for interval in self.intervals:
            if interval[1] < start or interval[0] > end:  # No overlap
                new_intervals.add(interval)
            else:  # Merge overlapping intervals
                to_add = (min(to_add[0], interval[0]), max(to_add[1], interval[1]))
        new_intervals.add(to_add)
        self.intervals = new_intervals

    def remove_interval(self, start, end):
        """
        Removes an interval, adjusting or splitting existing intervals as necessary.
        """
        new_intervals = set()
        for interval in self.intervals:
            if interval[1] < start or interval[0] > end:  # No overlap, keep interval
                new_intervals.add(interval)
            else:
                # Adjust or split interval if there's any overlap
                if interval[0] < start:
                    new_intervals.add((interval[0], start - 1))
                if interval[1] > end:
                    new_intervals.add((end + 1, interval[1]))
        self.intervals = new_intervals  # Update intervals

    def find_largest_interval(self):
        """
        Finds and returns the largest interval by length.
        """
        if not self.intervals:
            return None  # No intervals to compare
        return max(self.intervals, key=lambda x: x[1] - x[0])

    def print_intervals(self):
        """
        Prints all intervals sorted by their start value.
        """
        for interval in sorted(list(self.intervals)):
            print(interval)
