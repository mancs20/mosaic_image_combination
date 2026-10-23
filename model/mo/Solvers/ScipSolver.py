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
from pyscipopt import SCIP_STAGE

ONLY_SAUGMECON = "SCIP is only supported with the Saugmecon front generator"


class ScipSolver(Solver):
    """SCIP through PySCIPOpt, the counterpart of GurobiSolver.

    After a solve, SCIP only accepts changes to the problem (constraints, objective, sense) once the transformed problem
    is freed, and freeing it also frees the solutions. So the problem is freed lazily, just before the next change (see
    make_problem_modifiable): the solution of the last solve can be read until then, as the front generators do."""

    def __init__(self, model, statistics, threads, free_search=True):
        super().__init__(model, statistics, threads, free_search)
        self.objective_sense = "minimize"
        self.configure_feasibility_tolerance()
        self.disable_flower_separator()

    def disable_flower_separator(self):
        """The flower separator (new in SCIP 10, cuts for products of binary variables found by presolve) fails with
        "insufficient memory" on the large sims instances (tokyo_bay_200: about 600000 set packing constraints after
        presolve), with only 5 GB in use: it requests a huge allocation for its hypergraph, more memory does not help.
        The models are linear, they have no products of variables."""
        self.model.solver_model.setParam("separating/flower/freq", -1)

    def configure_feasibility_tolerance(self):
        """SCIP checks the constraints with a relative tolerance: a <= b is satisfied if
        (a - b) / max(|a|, |b|, 1) <= feastol. With large objective values (the clouds of sims are millions) the
        default feastol (1e-6) accepts "objective <= rhs" when the objective is rhs + 1, rhs + 2... and the
        e-constraints of the front generators are not enforced. Gurobi does not have this problem, its tolerance is
        absolute. The objectives are integer, so a violation of 1 must be rejected: feastol < 1 / largest value."""
        solver_model = self.model.solver_model
        largest_value = max([1.0] + [self.largest_absolute_value(objective) for objective in self.model.objectives])
        feastol = min(solver_model.getParam("numerics/feastol"), 0.5 / largest_value)
        epsilon = solver_model.getParam("numerics/epsilon")
        if feastol < epsilon:
            print(f"Warning: objective values up to {largest_value}, SCIP cannot tell apart differences of 1 with "
                  f"its precision (epsilon {epsilon})")
            feastol = epsilon
        solver_model.setParam("numerics/feastol", feastol)
        print(f"SCIP feasibility tolerance {feastol} (largest objective value {largest_value})")

    @staticmethod
    def largest_absolute_value(expression):
        # upper bound of |expression| from the bounds of its variables (linear expressions)
        largest_value = 0.0
        for term, coefficient in expression.terms.items():
            bound = 1.0
            for variable in term.vartuple:
                bound *= max(abs(variable.getLbOriginal()), abs(variable.getUbOriginal()))
            largest_value += abs(coefficient) * bound
        return largest_value

    def assert_right_solver(self, model):
        if model.solver_name != constants.Solver.SCIP.value:
            raise Exception(self.message_incorrect_solver())

    def set_solver(self):
        return None

    def set_threads(self, threads):
        # SCIP always runs with one thread: its branch and bound is sequential (the parallel/* parameters are only used
        # by solveConcurrent, never called here) and SoPlex, its LP solver, is sequential. lp/threads is set to 1 so it
        # stays sequential with an LP solver that can use threads
        self.model.solver_model.setParam("lp/threads", 1)
        if threads is not None and threads > 1:
            print(f"SCIP runs with one thread, {threads} threads were requested")

    def make_problem_modifiable(self):
        if self.model.solver_model.getStage() != SCIP_STAGE.PROBLEM:
            self.model.solver_model.freeTransform()

    def get_complete_solution(self):
        return self.model.solver_model

    def get_nodes_solution(self, solution):
        return solution.getNNodes()

    def get_solution_objective_values(self):
        one_solution = [self.model.solver_model.getVal(objective) for objective in self.model.objectives]
        # make sure the values of the objectives are rounded to the nearest integer
        one_solution = [int(round(x, 0)) for x in one_solution]
        self.model.review_objective_values(one_solution)
        return one_solution

    def set_minimization(self):
        self.objective_sense = "minimize"
        self.make_problem_modifiable()
        self.model.solver_model.setMinimize()

    def set_maximization(self):
        self.objective_sense = "maximize"
        self.make_problem_modifiable()
        self.model.solver_model.setMaximize()

    def set_time_limit(self, timeout_seconds):
        self.model.solver_model.setParam("limits/time", timeout_seconds)

    def reset(self):
        self.make_problem_modifiable()

    def get_status(self):
        return self.model.solver_model.getStatus()

    def status_time_limit(self):
        return self.get_status() == "timelimit"

    def status_infeasible(self):
        return self.get_status() in ("infeasible", "inforunbd")

    def supports_real_valued_objective(self):
        return True

    def configure_objective_resolution(self, min_difference):
        # same as GurobiSolver: no relative gap, and an absolute gap smaller than the smallest difference that must be
        # told apart, so the solution returned cannot be dominated by another one
        self.model.solver_model.setParam("limits/gap", 0.0)
        self.model.solver_model.setParam("limits/absgap", 0.95 * min_difference)

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
        raise NotImplementedError(ONLY_SAUGMECON)

    def change_objective_sense(self, id_objective):
        self.model.objectives[id_objective] = -self.model.objectives[id_objective]

    def set_single_objective(self, objective_expression):
        self.make_problem_modifiable()
        # setObjective clears the previous objective, the constant of the expression is the objective offset
        self.model.solver_model.setObjective(objective_expression, sense=self.objective_sense)

    def add_constraints_eq(self, constraint, rhs):
        self.make_problem_modifiable()
        return self.model.solver_model.addCons(constraint == rhs)

    def add_constraints_leq(self, constraint, rhs):
        self.make_problem_modifiable()
        return self.model.solver_model.addCons(constraint <= rhs)

    def add_constraints_geq(self, constraint, rhs):
        self.make_problem_modifiable()
        return self.model.solver_model.addCons(constraint >= rhs)

    def remove_constraint(self, constraint):
        self.make_problem_modifiable()
        self.model.solver_model.delCons(constraint)

    def opt_one_objective_or_satisfy(self, optimize_not_satisfy=True, verbose=False):
        if not optimize_not_satisfy:
            raise NotImplementedError(ONLY_SAUGMECON)
        self.model.solver_model.optimize()

    # used by the other front generators (Gavanelli, augmecon-coverage), not by Saugmecon ---------------------------
    def perform_lexicographic_optimization(self, verbose=False):
        raise NotImplementedError(ONLY_SAUGMECON)

    def deactivate_lexicographic_optimization(self):
        raise NotImplementedError(ONLY_SAUGMECON)

    def add_or_all_objectives_constraint(self, rhs, id_constraint=0):
        raise NotImplementedError(ONLY_SAUGMECON)

    def objs_smaller_equal_at_least_one_smaller(self, obj_constraints_lhs, rhs, id_constraint=0):
        raise NotImplementedError(ONLY_SAUGMECON)

    def lazy_constraints_possible(self):
        return False
