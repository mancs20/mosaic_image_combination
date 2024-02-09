import sys
import os

# Get the root directory
from pathlib import Path

script_path = Path(__file__).resolve()
pre_root_dir = script_path.parents[2]
root_dir = os.path.dirname(pre_root_dir)
# Add the root directory to sys.path
sys.path.append(root_dir)
# Import the module from the root directory
import constants
from model.mo.Solvers.Solver import Solver
import gurobipy as gp


class GurobiSolver(Solver):

    def __init__(self, model, statistics, threads, free_search=True):
        super().__init__(model, statistics, threads, free_search)

    def assert_right_solver(self, model):
        if model.solver_name != constants.Solver.GUROBI.value:
            raise Exception(self.message_incorrect_solver())

    def set_solver(self):
        return None

    def set_threads(self, threads):
        self.model.solver_model.Params.Threads = threads

    def get_complete_solution(self):
        return self.model.solver_model

    def get_nodes_solution(self, solution):
        return solution.NodeCount

    def get_solution_objective_values(self):
        one_solution = []
        for i in range(len(self.model.objectives)):
            if type(self.model.objectives[i]) == gp.Var:
                one_solution.append(self.model.objectives[i].x)
            else:
                one_solution.append(self.model.objectives[i].getValue())
        # make sure the values of the objectives are rounded down to the nearest integer
        one_solution = [int(round(x, 0)) for x in one_solution]
        self.model.review_objective_values(one_solution)
        return one_solution

    def set_minimization(self):
        self.model.solver_model.ModelSense = gp.GRB.MINIMIZE

    def set_maximization(self):
        self.model.solver_model.ModelSense = gp.GRB.MAXIMIZE

    def set_time_limit(self, timeout_seconds):
        self.model.solver_model.Params.TimeLimit = timeout_seconds

    def reset(self):
        self.model.solver_model.reset(1)

    def get_status(self):
        return self.model.solver_model.Status

    def status_time_limit(self):
        return self.model.solver_model.Status == gp.GRB.TIME_LIMIT

    def status_infeasible(self):
        return self.model.solver_model.Status == gp.GRB.INFEASIBLE

    def build_objective_e_constraint_saugmecon(self, range_array, augmentation):
        obj = self.model.objectives[0]
        delta = 0.001  # delta should be between 0.001 and 0.000001
        rest_obj = 0
        for i in range(len(range_array)):
            rest_obj += self.model.objectives[i + 1] / range_array[i]
        if augmentation:
            obj = obj + (delta * rest_obj)
        self.set_single_objective(obj)

    def set_single_objective(self, objective_expression):
        self.model.solver_model.setObjective(objective_expression)

    def add_constraints_eq(self, constraint, rhs):
        new_constraint = self.model.solver_model.addConstr(constraint == rhs)
        return new_constraint

    def add_constraints_leq(self, constraint, rhs):
        new_constraint = self.model.solver_model.addConstr(constraint <= rhs)
        return new_constraint

    def add_constraints_geq(self, constraint, rhs):
        new_constraint = self.model.solver_model.addConstr(constraint >= rhs)
        return new_constraint

    def remove_constraints(self, constraint):
        self.model.solver_model.remove(constraint)

    def opt_one_objective_or_satisfy(self, optimize_not_satisfy=True):
        if not optimize_not_satisfy:
            self.model.solver_model.Params.solutionLimit = 1
        self.model.solver_model.optimize()

    def perform_lexicographic_optimization(self):
        print("Performing lexicographic optimization is not implemnted yet for GurobiSolver.")
        raise NotImplementedError()

    def add_or_all_objectives_constraint(self, rhs, id_constraint=0):
        y = self.model.solver_model.addVars(len(self.model.objectives), vtype=gp.GRB.BINARY,
                                            name=f"temp_y_{id_constraint}")
        self.model.solver_model.addConstr(gp.quicksum(y) == 1)
        if self.model.is_a_minimization_model():
            rhs = [rhs[i] - 1 for i in range(len(rhs))]
        else:
            rhs = [rhs[i] + 1 for i in range(len(rhs))]
        big_m = self.get_big_m_for_or_all_objectives(rhs)
        for i in range(len(self.model.objectives)):
            if self.model.is_a_minimization_model():
                if self.can_big_m_introduce_problems(big_m[i]):
                    self.model.solver_model.addConstr((y[i] == 1) >> (self.model.objectives[i] <= rhs[i]),
                                                      name=f"indicator_const{id_constraint}_{i}")
                    self.model.solver_model.addConstr((y[i] == 0) >> (self.model.objectives[i] <= rhs[i] + big_m[i]),
                                                      name=f"indicator_const{id_constraint}_{i}")
                else:
                    self.model.solver_model.addConstr(self.model.objectives[i] <=
                                                      rhs[i] + (big_m[i] * (1 - y[i])))
            else:
                if self.can_big_m_introduce_problems(big_m[i]):
                    self.model.solver_model.addConstr((y[i] == 1) >> (self.model.objectives[i] >= rhs[i]),
                                                      name=f"indicator_const{id_constraint}_{i}")
                    self.model.solver_model.addConstr((y[i] == 0) >> (self.model.objectives[i] >= rhs[i] - big_m[i]),
                                                      name=f"indicator_const{id_constraint}_{i}")
                else:
                    self.model.solver_model.addConstr(self.model.objectives[i] >=
                                                      rhs[i] - (big_m[i] * (1 - y[i])))

    def get_big_m_for_or_all_objectives(self, rhs):
        big_m = []
        nadir_objectives = self.model.get_nadir_bound_estimation()
        for i in range(len(rhs)):
            big_m.append(abs(nadir_objectives[i] - rhs[i]))
        return big_m

    def can_big_m_introduce_problems(self, big_m):
        if big_m * self.model.solver_model.Params.IntFeasTol >= 1:
            return True
        return False
