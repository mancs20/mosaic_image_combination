from gurobipy import max_

import constants
from model.mo.MosaicCloudMIPmodel import MosaicCloudMIPmodel
from model.mo.Solvers.Solver import Solver
import gurobipy as gp


class GurobiSolver(Solver):

    def __init__(self, model, statistics, threads, free_search=True):
        super().__init__(model, statistics, threads, free_search)
        # self.elements, self.areas = gp.multidict({i: instance.areas[i] for i in range(len(instance.areas))})
        # self.images_id, self.images, self.costs = gp.multidict({i: [instance.images[i], instance.costs[i]]
        #                                                         for i in range(len(instance.images))})
        # # cloud processing
        # self.cloud_covered_by_image = gp.tupledict(instance.cloud_covered_by_image)
        # self.clouds_id, self.area_clouds = gp.multidict(instance.clouds_id_area)
        # self.total_area_clouds = int(sum(self.area_clouds.values()))
        # # resolution processing
        # self.resolution = gp.tupledict(zip(self.images_id, instance.resolution))
        # self.min_resolution = min(instance.resolution)
        # # incidence angle processing
        # self.incidence_angle = gp.tupledict(zip(self.images_id, instance.incidence_angle))
        # # multiply to convert to integers
        # # variables
        # self.select_image = None
        # self.cloud_covered = None
        # self.resolution_element = None
        # self.effective_image_resolution = None
        # self.effective_incidence_angle = None
        # self.current_max_incidence_angle = None
        # self.add_variables()
        # self.objectives = []
        # self.add_objectives()
        # self.constraint_objectives = [0] * len(self.objectives)

    def assert_right_solver(self, model):
        if model != constants.Solver.GUROBI:
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
        for i in range(len(self.objectives)):
            if type(self.objectives[i]) == gp.Var:
                one_solution.append(self.objectives[i].x)
            else:
                one_solution.append(self.objectives[i].getValue())
        # make sure the values of the objectives are rounded down to the nearest integer
        one_solution = [int(round(x, 0)) for x in one_solution]
        return one_solution

    # def get_selected_images(self):
    #     selected_images = []
    #     for image in self.select_image.keys():
    #         if abs(self.select_image[image].x) > 1e-6:
    #             selected_images.append(image)
    #     return selected_images

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

    def build_objective_e_constraint_saugmecon(self, range_array):
        obj = self.model.objectives[0]
        delta = 0.001 # delta should be between 0.001 and 0.000001
        rest_obj = 0
        for i in range(len(self.objectives)):
            rest_obj += self.objectives[i]/range_array[i]
        # todo to compare against cp augmentation has to be false
        augmenentation = True
        if augmenentation:
            obj = obj + (delta * rest_obj)
        self.set_single_objective(obj)
        self.set_minimization()
        # return obj

    def set_single_objective(self, objective_expression):
        self.model.solver_model.setObjective(objective_expression)

    def add_constraints_leq(self, constraint, rhs):
        new_constraint = self.model.solver_model.addConstr(constraint <= rhs)
        return new_constraint

    def remove_constraints(self, constraint):
        self.model.solver_model.remove(constraint)

    def solve(self, optimize_not_satisfy=True):
        if optimize_not_satisfy:
            self.model.solver_model.optimize()
        else:
            # todo do satisfiability
            pass