import math

import sys
import os
from enum import Enum

# Get the root directory
from pathlib import Path

from model.mo.Timer import Timer

script_path = Path(__file__).resolve()
pre_root_dir = script_path.parents[2]
root_dir = os.path.dirname(pre_root_dir)
# Add the root directory to sys.path
sys.path.append(root_dir)
# Import the module from the root directory
import constants
from model.mo.Solvers.Solver import Solver
from ortools.sat.python import cp_model
from ortools.sat import sat_parameters_pb2


class OrtoolsCPSolver(Solver):
    def __init__(self, model, statistics, threads, free_search=True):
        super().__init__(model, statistics, threads, free_search)
        self.status = None
        self.current_objective = None
        self.last_optimization = LastOptimization.NONE

    def assert_right_solver(self, model):
        if model.solver_name != constants.Solver.ORTOOLS_PY.value:
            raise Exception(self.message_incorrect_solver())

    def set_solver(self):
        return cp_model.CpSolver()

    def build_objective_e_constraint_saugmecon(self, range_array, augmentation):
        # ortools cannot work with floats, so we need to convert to ints
        if augmentation:
            # augmentation consist in adding a small portion of the other objectives to the main objective, it looks
            # like this for 3 objectives:
            # obj = main_obj + delta * (obj2/r2 + obj3/r3), where delta is a small number (10e-3,10e-6), r2 and r3 are
            # the range of the objectives 2 and 3, respectively
            # As ortools cannot work with floats, we need to multiply everything by r2*r3*10e3 (if delta is 10e-3),
            # so the expression becomes:
            # obj = main_obj * r2*r3*10e3 + (obj2 * r3 + obj3 * r2)
            # but this could be a huge number for ortools, so some times cannot be done.
            # The best we can do is to
            # divide everything by the gcd of the range_array, so the expression becomes:
            # obj = main_obj * r2*r3*10e3/gcd + (obj2 * r3/gcd + obj3 * r2/gcd)
            try_without_division = True
            obj = 0
            constraint_objectives_scaled = []
            # todo complete the code to work with augmentation without division

            main_obj = self.model.objectives[0] * 1000
            for obj_range in range_array:
                main_obj *= obj_range
            constraint_objectives_scaled = []
            obj_multiplier = [1] * len(self.model.objectives)
            obj_multiplier[0] = 1000
            for i in range(len(obj_multiplier)):
                for j in range(len(range_array)):
                    if j+1 != i:
                        obj_multiplier[i] *= range_array[j]
            lb_list = []
            up_list = []
            if try_without_division:
                for i in range(len(self.model.objectives)):
                    lb_list.append(self.model.objectives[i].Proto().domain[0] * obj_multiplier[i])
                    up_list.append(self.model.objectives[i].Proto().domain[-1] * obj_multiplier[i])
            else:
                # change the values of obj_multiplier to be the gcd of the obj_multiplier
                gcd = self.gcd(obj_multiplier)
                obj_multiplier = [int(x/gcd) for x in obj_multiplier]
            main_obj = self.model.solver_model.NewIntVar(sum(lb_list), sum(up_list), "main_obj")
            self.model.solver_model.Add(main_obj == sum(self.model.objectives[i] * obj_multiplier[i]
                                  for i in range(len(self.model.objectives))))
            self.current_objective = main_obj
        else:
            self.current_objective = self.model.objectives[0]

    def build_objective_e_constraint_augmecon2(self, best_constrain_obj_list, nadir_constrain_obj_list, augmentation):
        if len(self.model.objectives) != 2:
            raise Exception("The augmecon2 is implemented for 2 objectives only.")
        # todo add lb and up to the variables
        constraint_objectives = []
        if augmentation:
            delta = 1000
            max_s2 = abs(best_constrain_obj_list[1]-nadir_constrain_obj_list[1])
            s2 = self.model.solver_model.NewIntVar(lb=0, ub=max_s2, name="s2")
            # main objective
            min_obj = delta * min(nadir_constrain_obj_list[0], best_constrain_obj_list[0])
            max_obj = delta * max(nadir_constrain_obj_list[0], best_constrain_obj_list[0]) + max_s2
            obj = self.model.solver_model.NewIntVar(lb=min_obj, ub=max_obj, name="obj")
            self.model.solver_model.Add(obj == self.model.objectives[0] * delta + s2).WithName("obj_augmecon2")
            # constraint objectives
            min_obji = min(nadir_constrain_obj_list[1], best_constrain_obj_list[1])
            max_obji = max(nadir_constrain_obj_list[1], best_constrain_obj_list[1])
            obji_minus_s2 = self.model.solver_model.NewIntVar(lb=min_obji, ub=max_obji, name="obji_minus_s2_variable")
            self.model.solver_model.Add(obji_minus_s2 == self.model.objectives[1] - s2).WithName(
                "obji_minus_s2_constraint")
            constraint_objectives.append(obji_minus_s2)
            self.current_objective = obj
        else:
            self.current_objective = self.model.objectives[0]
            constraint_objectives.append(self.model.objectives[1])
        return constraint_objectives

    def change_objective_sense(self, id_objective):
        objective_to_change = self.model.objectives[id_objective]
        objective_proto = objective_to_change.Proto()
        lb = objective_proto.domain[0]
        ub = objective_proto.domain[1]
        objective_changed = self.model.solver_model.NewIntVar(lb=-ub, ub=-lb,
                                                              name=f"var_reversed_objective_{id_objective}")
        self.model.solver_model.Add(objective_changed == -objective_to_change).WithName(
            f"constrain_reversed_objective_{id_objective}")
        self.model.objectives[id_objective] = objective_changed

    def set_threads(self, threads):
        self.solver.parameters = sat_parameters_pb2.SatParameters(num_search_workers=threads)

    def opt_one_objective_or_satisfy(self, optimize_not_satisfy=True):
        self.status = self.solver.Solve(self.model.solver_model)
        if self.status == cp_model.INFEASIBLE:
            print("infeasible")
        elif self.status == cp_model.UNKNOWN:
            print("ortools-sat solver timeout")
        else:
            self.add_solution_values_to_model_solver_values()

    def perform_lexicographic_optimization(self):
        current_timeout_time = self.solver.parameters.max_time_in_seconds
        timer_lex = Timer(current_timeout_time)
        if len(self.lexicographic_obj_order) == 0:
            raise Exception("No lexicographic objective list is set.")
        lexico_constraints = []
        for i in range(len(self.lexicographic_obj_order)):
            self.set_single_objective(self.model.objectives[self.lexicographic_obj_order[i]])
            if self.last_optimization == LastOptimization.MINIMIZATION:
                self.set_minimization()
            elif self.last_optimization == LastOptimization.MAXIMIZATION:
                self.set_maximization()
            else:
                raise Exception("No optimization sense is set.")
            timeout = float(timer_lex.time_budget_sec)
            self.set_time_limit(timeout)
            if timeout <= 0:
                raise TimeoutError()
            timer_lex.resume()
            self.solver.Solve(self.model.solver_model)
            timer_lex.pause()
            # todo check how this could be infeasible
            one_solution = self.get_solution_objective_values()
            lexico_constraints.append(self.add_constraints_eq(self.model.objectives[self.lexicographic_obj_order[i]],
                                                              one_solution[self.lexicographic_obj_order[i]]))
        for constraints in lexico_constraints:
            self.remove_constraints(constraints)
        self.add_solution_values_to_model_solver_values()

    def add_solution_values_to_model_solver_values(self):
        self.model.solver_values = []
        for values in self.model.solution_variables:
            if type(values) == list:
                for value in values:
                    self.model.solver_values.append(self.solver.Value(value))
            else:
                self.model.solver_values.append(self.solver.Value(values))

    def add_constraints_eq(self, constraint, rhs):
        new_constraint = self.model.solver_model.Add(constraint == rhs)
        return new_constraint

    def add_constraints_leq(self, constraint, rhs):
        new_constraint = self.model.solver_model.Add(constraint <= rhs)
        return new_constraint

    def add_constraints_geq(self, constraint, rhs):
        new_constraint = self.model.solver_model.Add(constraint >= rhs)
        return new_constraint

    def remove_constraints(self, constraint):
        constraint.Proto().Clear()

    def set_minimization(self):
        self.model.solver_model.Minimize(self.current_objective)
        self.last_optimization = LastOptimization.MINIMIZATION

    def set_maximization(self):
        self.model.solver_model.Maximize(self.current_objective)
        self.last_optimization = LastOptimization.MAXIMIZATION

    def set_time_limit(self, timeout):
        self.solver.parameters.max_time_in_seconds = timeout

    def set_single_objective(self, objective_expression):
        self.current_objective = objective_expression

    def reset(self):
        return True

    def get_solution_objective_values(self):
        one_solution = []
        for i in range(len(self.model.objectives)):
            one_solution.append(self.solver.Value(self.model.objectives[i]))
        one_solution = [int(round(x, 0)) for x in one_solution]
        return one_solution

    def get_status(self):
        return self.solver.StatusName(self.status)

    def status_time_limit(self):
        return self.status == cp_model.UNKNOWN

    def status_infeasible(self):
        return self.status == cp_model.INFEASIBLE

    def get_complete_solution(self):
        return self.solver

    def get_nodes_solution(self, solution):
        # todo check if this is the best statistic to show
        return self.solver.NumBranches()

    def add_or_all_objectives_constraint(self, rhs, id_constraint=0, sense_min=True):
        if sense_min:
            obj_constraints = [self.model.objectives[i] < rhs[i] for i in range(len(rhs))]
        else:
            obj_constraints = [self.model.objectives[i] > rhs[i] for i in range(len(rhs))]
        bool_vars = [self.model.solver_model.NewBoolVar(f"or_all_objectives_{id_constraint}_{i}")
                     for i in range(len(self.model.objectives))]
        for i in range(len(self.model.objectives)):
            self.model.solver_model.Add(obj_constraints[i]).OnlyEnforceIf(bool_vars[i])
        pareto_constraints = self.model.solver_model.AddAtLeastOne(bool_vars)
        return pareto_constraints


    def gcd(self, list_to_gcd):
        gcd = list_to_gcd[0]
        for i in range(1, len(list_to_gcd)):
            gcd = math.gcd(gcd, list_to_gcd[i])
        return gcd


class LastOptimization(Enum):
    MINIMIZATION = 1
    MAXIMIZATION = 2
    NONE = 3
