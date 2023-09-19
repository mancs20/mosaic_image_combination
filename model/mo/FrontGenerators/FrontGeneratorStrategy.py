from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any


class FrontGeneratorStrategy(ABC):

    def __init__(self, instance, solver, timer):
        self.instance = instance
        self.solver = solver
        self.timer = timer
        self.ref_points = self.get_reference_points()

    def get_reference_points(self):
        ref_points = [sum(self.instance.costs) + 1, sum(self.instance.areas) + 1, self.get_resolution_nadir_for_ref_point() + 1, 900]
        return ref_points

    def get_resolution_nadir_for_ref_point(self):
        resolution_parts_max = {}
        for idx, image in enumerate(self.instance.images):
            for u in image:
                if u not in resolution_parts_max:
                    resolution_parts_max[u] = self.instance.resolution[idx]
                else:
                    if resolution_parts_max[u] < self.instance.resolution[idx]:
                        resolution_parts_max[u] = self.instance.resolution[idx]
        return sum(resolution_parts_max.values())

    def get_upper_bound_nadir(self):
        nadir_objectives = [sum(self.instance.areas), self.get_resolution_nadir_for_ref_point(), max(self.instance.incidence_angle)]
        return nadir_objectives

    @abstractmethod
    def solve(self):
        pass

    def prepare_solution(self):
        one_solution = self.solver.get_solution_values()
        selected_images = self.solver.get_selected_images()
        taken = [False] * len(self.instance.images)
        for image in selected_images:
            taken[image] = True
        ref_points = self.ref_points
        # ef_array = copy.deepcopy(ef_array)
        solution = Solution(objs=one_solution, taken=taken,
                            minimize_objs=[True] * len(one_solution), ref_point=ref_points)
        status = self.solver.get_status()
        statistics = None
        minizinc_formatted_solution = MinizincResultFormat(status=status, solution=solution, statistics=statistics)
        return minizinc_formatted_solution


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
    # ef_array: List[int]


