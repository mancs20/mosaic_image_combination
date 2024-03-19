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

# todo this callback apparently is working
# def add_unsatisfaction_constraint_callback(model, where):
#     if where == gp.GRB.Callback.MIPSOL:
#         selected_images = model.cbGetSolution(model._vars)
#         model._vals = selected_images


class GurobiSolver(Solver):

    def __init__(self, model, statistics, threads, free_search=True):
        super().__init__(model, statistics, threads, free_search)
        self.latest_solution = None
        self.latest_values_decision_variables = None
        self.use_lazy_constraints = False
        self.auxiliary_variables_objs_smaller_equal_at_least_one_smaller = None

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
        # return solution.SolCount

    def get_solution_objective_values(self):
        one_solution = []
        for i in range(len(self.model.objectives)):
            if type(self.model.objectives[i]) is gp.Var:
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

    def build_objective_e_constraint_augmecon2(self, best_constrain_obj_list, nadir_constrain_obj_list, augmentation):
        raise NotImplementedError()

    def change_objective_sense(self, id_objective):
        raise NotImplementedError()

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

    def remove_constraint(self, constraint):
        self.model.solver_model.remove(constraint)

    def opt_one_objective_or_satisfy(self, optimize_not_satisfy=True, verbose=False):
        if not optimize_not_satisfy:
            self.model.solver_model.Params.solutionLimit = 1
            self.model.solver_model.Params.MIPFocus = 1
            # self.model.solver_model.Params.Cuts = 3
        if self.use_lazy_constraints:
            self.model.solver_model.Params.lazyConstraints = 1
            self.latest_solution = None
            self.latest_values_decision_variables = None
            # self.model.solver_model.optimize(self.add_unsatisfaction_constraint_callback)
            self.model.solver_model._objectivesval = self.model.objectives_val
            # todo the commented line below was working with the method outside the class
            self.model.solver_model._vars = self.model.select_image
            # self.model.solver_model._vals = None
            # self.model.solver_model.optimize(add_unsatisfaction_constraint_callback)
            self.model.solver_model.optimize(
                lambda model, where: self.add_unsatisfaction_constraint_callback(model, where))
        else:
            self.model.solver_model.optimize()

    def perform_lexicographic_optimization(self, verbose=False):
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

    def objs_smaller_equal_at_least_one_smaller(self, obj_constraints_lhs, rhs, id_constraint=0):
        new_constraints = []
        for i in range(len(obj_constraints_lhs)):
            new_constraints.append(self.model.solver_model.addConstr(
                obj_constraints_lhs[i] <= rhs[i] - self.auxiliary_variables_objs_smaller_equal_at_least_one_smaller[i]))
        return new_constraints

    # todo create this method for all solvers in constraint solvers it will be empty
    def create_variable_for_constraint_objs_smaller_equal_at_least_one_smaller(self):
        if self.auxiliary_variables_objs_smaller_equal_at_least_one_smaller is None:
            self.auxiliary_variables_objs_smaller_equal_at_least_one_smaller = self.model.solver_model.addVars(
                len(self.model.objectives), vtype=gp.GRB.BINARY)
            auxiliary_constraint = self.model.solver_model.addConstr(gp.quicksum(
                self.auxiliary_variables_objs_smaller_equal_at_least_one_smaller) >= 1)

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

    def add_unsatisfaction_constraint_callback(self, model, where):
        if where == gp.GRB.Callback.MIPSOL:
            # Get the solution
            deciaion_variables_value = model.cbGetSolution(model._vars)
            # selected_images = []
            # for i in range(len(selected_images_model)):
            #     if selected_images_model[i] > 0.5:
            #         selected_images.append(i)
            # model._vals = selected_images
            # obj = [self.model.calculate_cost(selected_images), self.model.calculate_cloud_covered(selected_images)]
            obj_model = model.cbGetSolution(model._objectivesval)
            # if obj_model != obj:
            #     stop_debug = True
            #     print("IMPORTANT THIS SHOULD NOT HAPPEN !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            self.latest_solution = obj_model
            self.latest_values_decision_variables = deciaion_variables_value
            # Get the unsatisfaction
            for i in range(len(self.model.objectives)):
                self.model.solver_model.cbLazy(self.model.objectives[i] <= obj_model[i] -
                                               self.auxiliary_variables_objs_smaller_equal_at_least_one_smaller[i])

    def lazy_constraints_possible(self):
        return True
