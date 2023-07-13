from typing import Any, List

from MosaicCloudMIPmodel import MosaicCloudMIPmodel
from OSolve import OSolve
import gurobipy as gp
from gurobipy import *
import copy
from dataclasses import dataclass

class OSolveMIP(OSolve):

    def __init__(self, instance, statistics, timer, threads=None, free_search=False):
        super().__init__(instance, statistics, timer, threads, free_search)
        self.images = None
        self.costs = None
        self.areas = None
        self.clouds = None
        self.max_cloud_area = None
        self.resolution = None
        self.incidence_angle = None
        self.get_data_from_model()
        self.ref_points = self.get_reference_points()
        self.cloud_covered_by_image, self.clouds_id_area = OSolveMIP.get_clouds_covered_by_image(self.clouds, self.images,
                                                                                            self.areas)
        self.mosaic_model = self.initialize_model()

    def get_data_from_model(self, image_id_start=0):
        self.images = self.instance["images"]
        self.costs = self.instance["costs"]
        self.areas = self.instance["areas"]
        self.clouds = self.instance["clouds"]
        if image_id_start == 0:  # Minizinc the id starts at 1
            for i in range(len(self.images)):
                self.images[i] = {x - 1 for x in self.images[i]}
            for i in range(len(self.clouds)):
                self.clouds[i] = {x - 1 for x in self.clouds[i]}
        for i in range(len(self.clouds)):
            if len(self.clouds[i]) == 0:
                self.clouds[i] = {}

        self.max_cloud_area = self.instance["max_cloud_area"]
        self.resolution = self.instance["resolution"]
        self.incidence_angle = self.instance["incidence_angle"]

    @staticmethod
    def get_clouds_covered_by_image(clouds, images, areas):
        cloud_covered_by_image = {}
        clouds_id_area = {}
        for i in range(len(clouds)):
            image_cloud_set = clouds[i]
            for cloud_id in image_cloud_set:
                if cloud_id not in clouds_id_area:
                    clouds_id_area[cloud_id] = areas[cloud_id]
                for j in range(len(images)):
                    if i != j:
                        if cloud_id in images[j] and cloud_id not in clouds[
                            j]:  # the area of the cloud is covered by image j, and it is not cloudy in j
                            if j in cloud_covered_by_image:
                                cloud_covered_by_image[j].add(cloud_id)
                            else:
                                cloud_covered_by_image[j] = {cloud_id}
        return cloud_covered_by_image, clouds_id_area

    def initialize_model(self):

        mosaic_model = MosaicCloudMIPmodel(self.images,self.costs,self.areas,self.cloud_covered_by_image,
                                           self.clouds_id_area,self.max_cloud_area,self.resolution,self.incidence_angle,
                                           model=gp.Model("mosaic_cloud_mip"))
        mosaic_model.add_basic_constraints()
        mosaic_model.model.Params.Threads = self.threads
        return mosaic_model

    def solve(self):
        formatted_solutions, min_objectives, nadir_objectives = self.initialize_model_with_e_constraint()
        # check if the solver could find the optimum for each objective
        for formatted_solution in formatted_solutions:
            if formatted_solution is not None:
                yield formatted_solution
            else:
                raise TimeoutError()
        # initialize loop-control variables with values equal to the nadir values + 1
        ef_array = [nadir_objectives[i] + 1 for i in range(len(nadir_objectives))]
        rwv = copy.deepcopy(min_objectives)
        previous_solutions = set()
        # add initial objective constraints
        self.mosaic_model.add_objective_constraints(ef_array)
        previous_solution_information = []
        while ef_array[2] > min_objectives[2]:
            ef_array[2] -= 1
            rwv[1] = min_objectives[1]
            while ef_array[1] > min_objectives[1]:
                ef_array[1] -= 1
                while ef_array[0] > min_objectives[0]:
                    ef_array[0] -= 1
                    previous_solution_relaxation, previous_solution_values = \
                        self.search_previous_solutions_relaxation(ef_array, previous_solution_information)
                    if not previous_solution_relaxation:
                        # update right-hand side values (rhs) for the objective constraints
                        self.mosaic_model.update_objective_constraints(ef_array)
                        # TODO add parameters, like timeout to the model
                        timeout = self.timer.resume()
                        print("Start the MIP solver...")
                        self.mosaic_model.model.Params.TimeLimit = timeout.total_seconds()
                        self.mosaic_model.model.optimize()
                        print("Got a result from the MIP solver...")
                        cp_sec = self.timer.pause()
                    if self.mosaic_model.model.Status == gp.GRB.TIME_LIMIT:
                        raise TimeoutError()
                    elif self.mosaic_model.model.Status == gp.GRB.INFEASIBLE or (previous_solution_relaxation and
                                                                          type(previous_solution_values) is str):
                        if not previous_solution_relaxation:
                            # save ef_array
                            self.save_solution_information(ef_array, "infeasible", previous_solution_information)
                        ef_array = self.exit_from_loop_with_acceleration(ef_array, nadir_objectives, min_objectives)
                    else:
                        if not previous_solution_relaxation:
                            selected_images = self.get_selected_images()
                            str_selected_images = '-'.join((str(i) for i in selected_images))
                            if str_selected_images in previous_solutions:
                                one_solution = self.get_solution_values()
                            else:
                                # update previous_solutions
                                previous_solutions.add(str_selected_images)
                                # update statistics
                                self.update_statistics(self.mosaic_model.model, cp_sec)
                                # record the solution
                                formatted_solution = self.prepare_solution()
                                one_solution = formatted_solution["objs"]
                                previous_solution_information = self.save_solution_information(ef_array, one_solution,
                                                                                          previous_solution_information)
                                yield formatted_solution
                        else:
                            one_solution = previous_solution_values
                        ef_array[0] = one_solution[1]  # one_solution[0] is the main objective
                        # Explore the relatively worst values rwv of objectives
                        rwv = self.explore_new_relatively_worst_values_of_objectives(rwv, one_solution, minimization=True)
                ef_array[0] = nadir_objectives[0] + 1
                if ef_array[1] > min_objectives[1]:
                    ef_array[1] = rwv[1]
                    rwv[1] = min_objectives[1]
            ef_array[1] = nadir_objectives[1] + 1
            if ef_array[2] > min_objectives[2]:
                ef_array[2] = rwv[2]
                rwv[2] = min_objectives[2]
        print("All solutions were found for " + self.statistics['instance'])

    def prepare_solution(self):
        one_solution = self.get_solution_values()
        selected_images = self.get_selected_images()
        taken = [False] * len(self.images)
        for image in selected_images:
            taken[image] = True
        ref_points = self.ref_points
        solution = Solution(objs=one_solution, taken=taken,
                            minimize_objs=[True] * len(one_solution), ref_point=ref_points)
        status = self.mosaic_model.model.Status
        statistics = None
        minizinc_formatted_solution = MinizincResultFormat(status=status, solution=solution, statistics=statistics)
        return minizinc_formatted_solution

    def get_reference_points(self):
        ref_points = [sum(self.costs) + 1, sum(self.areas) + 1, self.get_resolution_nadir_for_ref_point() + 1, 900]
        return ref_points

    def get_resolution_nadir_for_ref_point(self):
        resolution_parts_max = {}
        for idx, image in enumerate(self.images):
            for u in image:
                if u not in resolution_parts_max:
                    resolution_parts_max[u] = self.resolution[idx]
                else:
                    if resolution_parts_max[u] < self.resolution[idx]:
                        resolution_parts_max[u] = self.resolution[idx]
        return sum(resolution_parts_max.values())

    def get_solution_values(self):
        one_solution = [self.mosaic_model.get_main_objective().getValue()]
        for i in range(len(self.mosaic_model.objectives)):
            if type(self.mosaic_model.objectives[i]) == gp.Var:
                one_solution.append(self.mosaic_model.objectives[i].x)
            else:
                one_solution.append(self.mosaic_model.objectives[i].getValue())
        # make sure the values of the objectives are rounded down to the nearest integer
        one_solution = [int(round(x, 0)) for x in one_solution]
        return one_solution

    @staticmethod
    def exit_from_loop_with_acceleration(ef_array, nadir_objectives, min_objectives):
        i = 0
        while i < (len(ef_array) - 1) and ef_array[i] == nadir_objectives[i]:
            i += 1
        for j in range(i + 1):
            ef_array[j] = min_objectives[j]
        return ef_array

    @staticmethod
    def explore_new_relatively_worst_values_of_objectives(rwv, one_solution, minimization=True):
        # one_solution[0] is the main objective
        if minimization:
            for i in range(len(rwv)):
                if one_solution[i + 1] > rwv[i]:
                    rwv[i] = one_solution[i + 1]
        else:
            print("one_solution: ", one_solution)
            print("rwv: ", rwv)
            for i in range(len(rwv)):
                if one_solution[i + 1] < rwv[i]:
                    rwv[i] = one_solution[i + 1]
        return rwv

    def get_selected_images(self):
        selected_images = []
        for image in self.mosaic_model.select_image.keys():
            if abs(self.mosaic_model.select_image[image].x) > 1e-6:
                selected_images.append(image)
        return selected_images

    @staticmethod
    def save_solution_information(ef_array, solution, previous_solution_information):
        ef_array_to_insert = ef_array.copy()
        # insert the new solution in the correct position
        lo = OSolveMIP.id_insort_right_previous_solutions(ef_array_to_insert, previous_solution_information)
        previous_solution_information.insert(lo, [ef_array_to_insert, solution])
        return previous_solution_information

    @staticmethod
    def id_insort_right_previous_solutions(ef_array, previous_solution_information):
        lo = OSolveMIP.bisect_right_previous_solutions(ef_array, previous_solution_information)
        return lo

    @staticmethod
    def bisect_right_previous_solutions(ef_array, previous_solution_information):
        lo = 0
        hi = len(previous_solution_information)
        while lo < hi:
            mid = (lo + hi) // 2
            if ef_array > previous_solution_information[mid][0]:
                hi = mid
            else:
                lo = mid + 1
        return lo

    def search_previous_solutions_relaxation(self, ef_array_actual_solution, previous_solution_information):
        there_is_relaxation_for_ef_array_actual_solution = False
        if len(previous_solution_information) == 0:
            return there_is_relaxation_for_ef_array_actual_solution, None

        # find closer relaxation and check if the solution satisfy the ef_array_actual_solution
        previous_closer_relaxation = self.get_closer_relaxation(ef_array_actual_solution, previous_solution_information)
        if previous_closer_relaxation is False:
            return there_is_relaxation_for_ef_array_actual_solution, None
        else:
            f_solution_values = previous_closer_relaxation[1]
            there_is_relaxation_for_ef_array_actual_solution = True
            if type(f_solution_values) is not str:
                f_solution_values_for_constraint = f_solution_values[1:len(f_solution_values)]
                if not self.solution_satisfy_ef_arr(f_solution_values_for_constraint, ef_array_actual_solution):
                    there_is_relaxation_for_ef_array_actual_solution = False

        return there_is_relaxation_for_ef_array_actual_solution, f_solution_values

    def get_closer_relaxation(self, ef_array_actual_solution, previous_solution_information):
        idx = self.bisect_right_previous_solutions(ef_array_actual_solution, previous_solution_information)
        if idx == 0:
            return False
        return previous_solution_information[idx - 1]

    @staticmethod
    def solution_satisfy_ef_arr(solution_values, ef_arr):
        satisfy = True
        for i in range(len(ef_arr)):
            if solution_values[i] > ef_arr[i]:
                satisfy = False
                break
        return satisfy

    def initialize_model_with_e_constraint(self):
        formatted_solutions, min_objectives = self.get_min_objectives()
        if None in formatted_solutions:
            return formatted_solutions, min_objectives, None
        nadir_objectives = self.get_nadir_objectives()  # in this case, the nadir is the max
        # prepare the model for the e-constraint method
        self.mosaic_model.model.ModelSense = gp.GRB.MINIMIZE
        range_array = [abs(nadir_objectives[i] - min_objectives[i]) for i in range(len(nadir_objectives))]
        self.mosaic_model.optimize_e_constraint(range_array)
        return formatted_solutions, min_objectives, nadir_objectives

    def get_min_objectives(self):
        objectives_values = [0] * len(self.mosaic_model.objectives)
        formatted_solutions = [0] * len(self.mosaic_model.objectives)
        sense = GRB.MINIMIZE
        for i in range(len(self.mosaic_model.objectives)):
            formatted_solution, objective_val = self.optimize_single_objectives(sense, i)
            objectives_values[i] = objective_val
            formatted_solutions[i] = formatted_solution
            if formatted_solution is None:
                 break
        return formatted_solutions, objectives_values

    def get_nadir_objectives(self):
        nadir_objectives = self.get_upper_bound_nadir()
        return nadir_objectives

    def optimize_single_objectives(self, sense, id_objective):
        objective = self.mosaic_model.objectives[id_objective]
        timeout = self.timer.resume()
        print("Start the MIP solver to get the min of objective " + str(id_objective))
        self.mosaic_model.model.Params.TimeLimit = timeout.total_seconds()
        self.mosaic_model.model.setObjective(objective, sense)
        # TODO add parameters, like timeout to the model
        self.mosaic_model.model.optimize()
        cp_sec = self.timer.pause()
        print("MIP solver found min of objective " + str(id_objective) + " in " + str(cp_sec) + " seconds")
        if self.mosaic_model.model.Status == gp.GRB.TIME_LIMIT:
            return None, None
        formatted_solution = self.prepare_solution()
        objective_val = formatted_solution['objs'][id_objective+1]
        self.update_statistics(self.mosaic_model.model, cp_sec)
        self.mosaic_model.model.reset(1)
        return formatted_solution, objective_val

    def get_upper_bound_nadir(self):
        nadir_objectives = [sum(self.areas), self.get_resolution_nadir_for_ref_point(), max(self.incidence_angle)]
        return nadir_objectives


    def update_statistics(self, res, cp_sec):
        self.statistics["time_cp_sec"] += cp_sec
        if res is None:
            return
        self.statistics["cp_total_nodes"] += res.NodeCount
        self.statistics["time_fzn_sec"] += 0 # TODO add time_fzn_sec
        self.statistics["cp_solutions"] += 1
        self.statistics["cp_solutions_list"].append(self.statistics["time_cp_sec"])

@dataclass
class MinizincResultFormat:
    status: None
    solution: Any
    statistics: None
    def __getitem__(self, key):
        if isinstance(self.solution, list):
            if isinstance(key, tuple):
                return getattr(self.solution.__getitem__(key[0]), key[1])
            else:
                return self.solution.__getitem__(key)
        else:
            return getattr(self.solution, key)

@dataclass
class Solution:
    objs: List[int]
    minimize_objs: List[bool]
    taken: List[bool]
    ref_point: List[int]