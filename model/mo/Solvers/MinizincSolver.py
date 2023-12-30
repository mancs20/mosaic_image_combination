from minizinc import Status
import minizinc

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
from datetime import timedelta


class MinizincSolver(Solver):
    def __init__(self, model, instance, statistics, threads, free_search, optimisation_level):
        # self.model = model
        self.instance = instance
        # self.free_search = free_search
        self.optimisation_level = optimisation_level
        # self.statistics = statistics
        self.threads = None
        self.timeout = 0
        self.solver_solution = None
        self.local_constraints = ""
        super().__init__(model, statistics, threads, free_search)


    def set_solver(self):
        return None

    def set_threads(self, threads):
        self.threads = threads

    def solve(self, optimize_not_satisfy=True):
        with self.instance.branch() as child:
            child.add_string(self.local_constraints)
            while True:
                try:
                    self.solver_solution = child.solve(
                        optimisation_level=self.optimisation_level,
                        all_solutions=False,
                        free_search=self.free_search,
                        timeout=self.timeout,
                        processes=self.threads)
                    print("Got a result from the solver using Minizinc...")
                    break
                except minizinc.error.MiniZincError:
                    print("Minizinc or solver crashed... Retrying...")  # It can happen with GeCode in parallel mode.
        if self.solver_solution.status == Status.SATISFIED or self.solver_solution.status == Status.ALL_SOLUTIONS:
            return self.solver_solution
        elif self.solver_solution.status == Status.UNKNOWN:  # timeout
            raise TimeoutError()
        elif self.solver_solution.status == Status.ERROR:
            raise Exception("CP solver error\n")

    def add_constraints_leq(self, constraint, rhs):
        raise NotImplementedError()

    def add_constraints_geq(self, constraint, rhs):
        raise NotImplementedError()

    def remove_constraints(self, constraint):
        raise NotImplementedError()

    def set_minimization(self):
        raise NotImplementedError()

    def set_maximization(self):
        raise NotImplementedError()

    def set_time_limit(self, timeout):
        self.timeout = timedelta(seconds = timeout)

    def set_single_objective(self, objective_expression):
        raise NotImplementedError()

    def build_objective_e_constraint_saugmecon(self, range_array, augmentation):
        raise NotImplementedError()

    def reset(self):
        return True

    def get_solution_objective_values(self):
        return self.solver_solution.solution.objs

    def get_status(self):
        return self.solver_solution.status.name

    def status_time_limit(self):
        return self.solver_solution.status == Status.UNKNOWN

    def status_infeasible(self):
        return self.solver_solution.status == Status.UNSATISFIABLE

    def get_complete_solution(self):
        return self.solver_solution

    def add_or_all_objectives_constraint(self, rhs, id_constraint=0, sense_min=True):
        cons = []
        for i, minimize in enumerate(self.solver_solution['minimize_objs']):
            # obj_value = int(self.solver_solution["objs"][i])
            obj_value = int(rhs[i])
            if minimize:
                cons.append(f"objs[{i + 1}] < {obj_value}")
            else:
                cons.append(f"objs[{i + 1}] > {obj_value}")
        all_objective_or_cons = " \\/ ".join(cons)
        self.add_local_constraint(all_objective_or_cons)

    def get_nodes_solution(self, solution):
        nodes = 0
        if "nodes" in solution.statistics:
            self.statistics["total_nodes"] += solution.statistics["nodes"]
        else:
            print("No nodes info in statistics")
        return nodes

    def get_flat_time_secs(self, solution):
        flat_time = 0
        if "flatTime" in solution.statistics:
            flat_time = solution.statistics["flatTime"].total_seconds()
        else:
            print("No flatTime info in statistics")
        return flat_time

    def assert_right_solver(self, model):
        if model.solver_name != constants.Solver.MINIZINC.value:
            raise Exception(self.message_incorrect_solver())

    def add_local_constraint(self, constraint):
        """Add a constraint to the model only for the next call to `solve`."""
        if constraint != "true":
            self.local_constraints += "constraint " + constraint + ";\n"