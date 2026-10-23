from abc import ABC, abstractmethod

from model.mo.Models.GenericModel import GenericModel
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


class RcpspGenericModel(GenericModel, ABC):
    """Multi-objective RCPSP (makespan, weighted earliness-tardiness), time-indexed MILP: the DDT formulation (discrete
    time, disaggregated precedences) of Christofides et al. (1987), as compared by Kone et al. (2011), based on the
    time-indexed model of Pritsker et al. (1969).

        x[j, t] = 1 if task j starts at time t, t in the window [ES_j, LS_j]
        sum_t x[j, t] = 1                                                   for all j
        sum_{tau <= t} x[j, tau] <= sum_{tau <= t - d_i} x[i, tau]         for all i, j in suc(i), t (DDT)
        sum_j rr[r, j] * sum_{tau = t - d_j + 1}^{t} x[j, tau] <= rc[r]     for all r, t
        min makespan = sum_t t * x[n, t]                                    (start of the last task)
        min wet = sum_j sum_t c_j(t) * x[j, t]

    It reproduces rcpsp-wet-mkspan.mzn: start times in 0..t_max - 1 with t_max = sum of the durations, makespan = start
    of the last task, earliness-tardiness of the start time with respect to the due date, for all the tasks (the dummy
    source and sink too). The two options below change the last two points (to fix the data later), they must match
    the MiniZinc model used with Choco."""

    # True: earliness-tardiness of the completion time (start + duration) instead of the start time
    WET_ON_COMPLETION_TIME = False
    # True: the dummy source and sink (first and last task) are not part of the earliness-tardiness
    WET_ONLY_REAL_ACTIVITIES = False
    # False: aggregated precedences S_i + d_i <= S_j (one constraint per arc, weaker linear relaxation)
    DISAGGREGATED_PRECEDENCES = True

    def __init__(self, instance):
        self.start = None  # start[j][t]: variable x[j, t], t in window(j)
        self.earliest_start = []
        self.latest_start = []
        super().__init__(instance)

    def problem_name(self):
        return constants.Problem.RCPSP_WET_MAKESPAN_PROBLEM.value

    def is_a_minimization_model(self):
        return True

    def is_numerically_possible_augment_objective(self):
        return True

    # data -----------------------------------------------------------------------------------------------------------
    def get_data_from_instance(self):
        instance = self.instance
        self.n_tasks = instance.n_tasks
        self.last_task = instance.n_tasks - 1
        order = self.topological_order()
        # earliest start: longest path from the start of the project
        self.earliest_start = [0] * self.n_tasks
        for i in order:
            for j in instance.successors[i]:
                self.earliest_start[j] = max(self.earliest_start[j], self.earliest_start[i] + instance.durations[i])
        # latest start: every start time is at most t_max - 1, minus the longest path to the end of the project
        tail = [0] * self.n_tasks
        for i in reversed(order):
            for j in instance.successors[i]:
                tail[i] = max(tail[i], instance.durations[i] + tail[j])
        self.latest_start = [instance.t_max - 1 - tail[j] for j in range(self.n_tasks)]
        if any(self.earliest_start[j] > self.latest_start[j] for j in range(self.n_tasks)):
            raise Exception("The horizon is shorter than the critical path")

    def topological_order(self):
        predecessors_count = [0] * self.n_tasks
        for i in range(self.n_tasks):
            for j in self.instance.successors[i]:
                predecessors_count[j] += 1
        order = [i for i in range(self.n_tasks) if predecessors_count[i] == 0]
        for i in order:
            for j in self.instance.successors[i]:
                predecessors_count[j] -= 1
                if predecessors_count[j] == 0:
                    order.append(j)
        if len(order) != self.n_tasks:
            raise Exception("The precedence graph has a cycle")
        return order

    def window(self, j):
        return range(self.earliest_start[j], self.latest_start[j] + 1)

    def wet_cost(self, j, t):
        """Earliness-tardiness cost of starting task j at time t."""
        instance = self.instance
        if self.WET_ONLY_REAL_ACTIVITIES and j in (0, self.last_task):
            return 0
        time = t + instance.durations[j] if self.WET_ON_COMPLETION_TIME else t
        return (instance.earliness_costs[j] * max(0, instance.due_dates[j] - time) +
                instance.tardiness_costs[j] * max(0, time - instance.due_dates[j]))

    # model (the solver specific models create the variables and turn the lists of terms into constraints) -----------
    @abstractmethod
    def add_variables_to_model(self):
        # self.start[j] = {t: binary variable for t in self.window(j)}
        pass

    @abstractmethod
    def linear_expression(self, terms):
        # terms: list of (coefficient, variable)
        pass

    @abstractmethod
    def add_linear_constraint(self, terms, sense, rhs, name):
        # sense: "<=", "==" or ">="
        pass

    def define_objectives(self):
        makespan = [(t, self.start[self.last_task][t]) for t in self.window(self.last_task)]
        wet = [(self.wet_cost(j, t), self.start[j][t]) for j in range(self.n_tasks) for t in self.window(j)
               if self.wet_cost(j, t) != 0]
        self.objectives.append(self.linear_expression(makespan))
        self.objectives.append(self.linear_expression(wet))

    def add_constraints_to_model(self):
        self.add_one_start_per_task()
        if self.DISAGGREGATED_PRECEDENCES:
            self.add_disaggregated_precedences()
        else:
            self.add_aggregated_precedences()
        self.add_resource_constraints()

    def add_one_start_per_task(self):
        for j in range(self.n_tasks):
            self.constraints.append(self.add_linear_constraint([(1, self.start[j][t]) for t in self.window(j)], "==", 1,
                                                               f"start_{j}"))

    def add_aggregated_precedences(self):
        durations = self.instance.durations
        for i in range(self.n_tasks):
            for j in self.instance.successors[i]:
                # S_j - S_i >= d_i
                terms = ([(t, self.start[j][t]) for t in self.window(j)] +
                         [(-t, self.start[i][t]) for t in self.window(i)])
                self.constraints.append(self.add_linear_constraint(terms, ">=", durations[i], f"prec_{i}_{j}"))

    def add_disaggregated_precedences(self):
        durations = self.instance.durations
        for i in range(self.n_tasks):
            for j in self.instance.successors[i]:
                # j started by t => i started by t - d_i. Redundant from t = LS_j: both sides are 1 (LS_i <= LS_j - d_i),
                # redundant too when i surely started by t - d_i (t - d_i >= LS_i)
                for t in range(self.earliest_start[j], min(self.latest_start[j], self.latest_start[i] + durations[i])):
                    terms = ([(1, self.start[j][tau]) for tau in range(self.earliest_start[j], t + 1)] +
                             [(-1, self.start[i][tau]) for tau in range(self.earliest_start[i],
                                                                       min(t - durations[i], self.latest_start[i]) + 1)])
                    self.constraints.append(self.add_linear_constraint(terms, "<=", 0, f"prec_{i}_{j}_{t}"))

    def add_resource_constraints(self):
        instance = self.instance
        end_of_horizon = max(self.latest_start[j] + instance.durations[j] for j in range(self.n_tasks))
        for r in range(instance.n_resources):
            tasks = [j for j in range(self.n_tasks) if instance.requirements[r][j] > 0 and instance.durations[j] > 0]
            if sum(instance.requirements[r][j] for j in tasks) <= instance.capacities[r]:
                continue  # as in the MiniZinc model: the capacity can never be exceeded
            for t in range(end_of_horizon):
                # task j is running at time t if it starts in [t - d_j + 1, t]
                terms = [(instance.requirements[r][j], self.start[j][tau]) for j in tasks
                         for tau in range(max(t - instance.durations[j] + 1, self.earliest_start[j]),
                                          min(t, self.latest_start[j]) + 1)]
                if sum(coefficient for coefficient, _ in terms) > instance.capacities[r]:
                    self.constraints.append(self.add_linear_constraint(terms, "<=", instance.capacities[r],
                                                                       f"resource_{r}_{t}"))

    # bounds -----------------------------------------------------------------------------------------------------------
    def get_nadir_bound_estimation(self):
        # same bounds as the MiniZinc model (and the reference point of the Choco results): the makespan is at most
        # t_max - 1, the earliness-tardiness at most the bound of the domain of wet
        instance = self.instance
        wet_bound = sum(max(instance.earliness_costs[j] * instance.due_dates[j],
                            instance.tardiness_costs[j] * (instance.t_max - instance.due_dates[j]))
                        for j in range(self.n_tasks))
        return [instance.t_max - 1, wet_bound]

    def get_ref_points_for_hypervolume(self):
        return self.get_nadir_bound_estimation()

    def review_objective_values(self, objective_values):
        pass

    @abstractmethod
    def start_time(self, j):
        # start time of task j in the solution
        pass

    def get_solution_values(self):
        # start time of each task, like decision_vars in the MiniZinc model
        return [self.start_time(j) for j in range(self.n_tasks)]

    def add_necessary_solver_configuration(self):
        print("Extra solver configuration no needed")
