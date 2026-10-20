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

    def supports_real_valued_objective(self):
        return True

    def configure_objective_resolution(self, min_difference):
        params = self.model.solver_model.Params
        # Gurobi stops when the relative gap (MIPGap * |objective|, 1e-4 by default) or the absolute gap (MIPGapAbs) is
        # reached. The relative gap depends on the size of the objective, it could be much larger than min_difference
        params.MIPGap = 0
        # the solution returned is worse than the optimum by at most MIPGapAbs. If it is smaller than min_difference,
        # the solution returned cannot be dominated by another one (it would be worse by at least min_difference)
        params.MIPGapAbs = 0.95 * min_difference

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
        if len(self.model.objectives) != 2:
            raise Exception("The augmecon2 is implemented for 2 objectives only.")
        constraint_objectives = []
        if augmentation:
            delta = 0.0001  # delta should be between 0.001 and 0.000001
            max_s2 = abs(best_constrain_obj_list[1] - nadir_constrain_obj_list[1])
            s2 = self.model.solver_model.addVar(vtype=gp.GRB.INTEGER, lb=0, ub=max_s2, name="s2")
            # main objective
            obj = self.model.objectives[0] + (delta * s2)
            self.set_single_objective(obj)
            # constraint objectives
            constraint_objectives.append(self.model.objectives[1] - s2)
        else:
            self.set_single_objective(self.model.objectives[0])
            constraint_objectives.append(self.model.objectives[1])
        return constraint_objectives


    def change_objective_sense(self, id_objective):
        self.model.objectives[id_objective] = -self.model.objectives[id_objective]

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
        if optimize_not_satisfy:
            self.model.solver_model.optimize()
        else:
            self.run_satisfaction()

    def run_satisfaction(self):
        self.model.solver_model.Params.solutionLimit = 1
        self.model.solver_model.Params.MIPFocus = 1
        self.model.solver_model.setObjective(0)
        # self.model.solver_model.Params.Cuts = 3
        if self.use_lazy_constraints:
            self.model.solver_model.Params.lazyConstraints = 1
            self.latest_solution = None
            self.latest_values_decision_variables = None
            self.model.solver_model._objectives_val = self.model.objectives_val
            self.model.solver_model._solution_vars = self.model.solution_variables
            # todo add code to differentiate between possible different lazy constraints
            self.model.solver_model.optimize(
                lambda model, where: self.add_unsatisfaction_constraint_callback(model, where))
        else:
            self.model.solver_model.optimize()

    def perform_lexicographic_optimization(self, verbose=False):
        priority = len(self.model.objectives)
        if self.model.solver_model.IsMultiObj == 0:
            # set the objectives
            for i in range(len(self.model.objectives)):
                self.model.solver_model.setObjectiveN(self.model.objectives[i], i,
                                                      priority - self.lexicographic_obj_order[i])
        else:
            # update the priorities
            for i in range(len(self.model.objectives)):
                self.model.solver_model.params.ObjNumber = i
                self.model.solver_model.ObjNPriority = priority - self.lexicographic_obj_order[i]
        self.model.solver_model.optimize()

    def deactivate_lexicographic_optimization(self):
        if self.model.solver_model.IsMultiObj != 0:
            self.lexicographic_obj_order = []
            self.model.solver_model.NumObj = 0
            self.model.solver_model.update()

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
            solution_variables_value = model.cbGetSolution(model._solution_vars)
            obj_model = model.cbGetSolution(model._objectives_val)
            bad_solution_generated = False
            for i in range(len(obj_model)):
                if not obj_model[i].is_integer():
                    obj_model[i] = round(obj_model[i])
            if self.latest_solution is None:
                self.latest_solution = self.model.get_nadir_bound_estimation()
            for i in range(len(obj_model)):
                if obj_model[i] > self.latest_solution[i]:
                    bad_solution_generated = True
                    break
            if not bad_solution_generated:
                self.latest_solution = obj_model
                self.latest_values_decision_variables = solution_variables_value
            for i in range(len(obj_model)):
                model.cbLazy(model._objectives_val[i] <= self.latest_solution[i] -
                             self.auxiliary_variables_objs_smaller_equal_at_least_one_smaller[i])

    def lazy_constraints_possible(self):
        return True
