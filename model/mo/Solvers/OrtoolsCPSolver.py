import math

import constants
from model.mo.Solvers.Solver import Solver
from ortools.sat.python import cp_model
from ortools.sat import sat_parameters_pb2

class OrtoolsCPSolver(Solver):
    def __init__(self, model, statistics, threads, free_search=True):
        super().__init__(model, statistics, threads, free_search)
        self.status = None
        self.current_objective = None

    def assert_right_solver(self, model):
        if model.solver_name != constants.Solver.ORTOOLS_PY.value:
            raise Exception(self.message_incorrect_solver())

    def set_solver(self):
        return cp_model.CpSolver()

    def build_objective_e_constraint_saugmecon(self, range_array):
        # ortools cannot work with floats, so we need to convert to ints
        multiply_to_convert_to_int = False
        if multiply_to_convert_to_int:
            gcd = self.gcd(range_array)
            range_array = [int(x/gcd) for x in range_array]
            main_obj_multiplier = 1000
            multiplication_of_range = 1
            for i in range_array:
                main_obj_multiplier *= i
                multiplication_of_range *= i
            multipliers = []
            for i in range(len(range_array)):
                multipliers.append(int(multiplication_of_range / range_array[i]))
            gcd = self.gcd(multipliers + [main_obj_multiplier])
            obj = int(main_obj_multiplier/gcd) * self.model.objectives[0]
            constraint_objectives_scaled = []
            for i in range(len(self.model.objectives)):
                multiplier = multipliers[i]
                lb = self.model.objectives[i].Proto().domain[0] * multiplier
                up = self.model.objectives[i].Proto().domain[-1] * multiplier
                constraint_objectives_scaled.append(self.model.solver_model.NewIntVar(lb, up, f"obj_constraint{i}"))
                self.model.solver_model.Add(constraint_objectives_scaled[i] == self.model.objectives[i] * multiplier)
            self.model.solver_model.Minimize(obj + sum(constraint_objectives_scaled))
        else:
            self.model.solver_model.Minimize(self.model.objectives[0])

    def set_threads(self, threads):
        self.solver.parameters = sat_parameters_pb2.SatParameters(num_search_workers=threads)

    def solve(self, optimize_not_satisfy=True):
        self.status = self.solver.Solve(self.model.solver_model)
        if self.status == cp_model.INFEASIBLE:
            print("infeasible")
        else:
            self.add_solution_values_to_model_solver_values()

    def add_solution_values_to_model_solver_values(self):
        self.model.solver_values = []
        for values in self.model.solution_variables:
            if type(values) == list:
                for value in values:
                    self.model.solver_values.append(self.solver.Value(value))
            else:
                self.model.solver_values.append(self.solver.Value(values))

    def add_constraints_leq(self, constraint, rhs):
        new_constraint = self.model.solver_model.Add(constraint <= rhs)
        return new_constraint

    def remove_constraints(self, constraint):
        constraint.Proto().Clear()

    def set_minimization(self):
        self.model.solver_model.Minimize(self.current_objective)

    def set_maximization(self):
        self.model.solver_model.Maximize(self.current_objective)

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
        # todo try to implement it for the general case where the objectives can be max or min
        obj_constraints = [self.model.objectives[i] < rhs[i] for i in range(len(rhs))]
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