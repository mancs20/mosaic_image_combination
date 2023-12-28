from abc import ABC

import constants
from model.mo.Models.GenericModel import GenericModel


class SatelliteImageMosaicSelectionGeneralModel(GenericModel, ABC):
    def __init__(self, instance):
        # variables
        self.select_image = None
        self.cloud_covered = None
        self.resolution_element = []
        self.effective_image_resolution = None
        self.effective_incidence_angle = None
        self.current_max_incidence_angle = None
        self.total_area_clouds = None
        super().__init__(instance)

    def problem_name(self):
        return constants.Problem.SATELLITE_IMAGE_SELECTION_PROBLEM.value

    def is_a_minimization_model(self):
        return True

    def get_nadir_bound_estimation(self):
        nadir_objectives = [0] * len(self.objectives)
        nadir_objectives[0] = sum(self.instance.costs)
        nadir_objectives[1] = sum(self.instance.areas)
        # todo uncomment after check the speed
        # nadir_objectives[2] = self.get_resolution_nadir_for_ref_point()
        # nadir_objectives[3] = max(self.instance.incidence_angle)
        return nadir_objectives

    def get_ref_points_for_hypervolume(self):
        ref_points = [0] * len(self.objectives)
        ref_points[0] = sum(self.instance.costs) + 1
        ref_points[1] = sum(self.instance.areas) + 1
        # todo uncomment after check the speed
        # ref_points[2] = self.get_resolution_nadir_for_ref_point() + 1
        # ref_points[3] = 900
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

    def assert_solution(self, solution, selected_images):
        self.assert_is_a_cover(selected_images)
        self.assert_cost(selected_images, solution[0])
        self.assert_cloud_covered(selected_images, solution[1])
        # todo uncomment after test is working
        # self.assert_resolution(selected_images, solution[2])
        # self.assert_incidence_angle(selected_images, solution[3])

    def assert_is_a_cover(self, selected_images):
        # check if it is a cover
        covered_elements = set()
        for image in selected_images:
            for element in self.instance.images[image]:
                covered_elements.add(element)
        assert len(covered_elements) == len(self.instance.areas)


    def assert_cost(self, selected_images, cost):
        total_cost = 0
        for image in selected_images:
            total_cost += self.instance.costs[image]
        assert total_cost == cost

    def assert_cloud_covered(self, selected_images, cloud_uncovered):
        total_cloud_covered = 0
        cloud_covered = set()
        for image in selected_images:
            if image in self.instance.cloud_covered_by_image:
                for cloud in self.instance.cloud_covered_by_image[image]:
                    if cloud not in cloud_covered:
                        cloud_covered.add(cloud)
                        total_cloud_covered += self.instance.clouds_id_area[cloud]
        total_area_clouds = int(sum(self.instance.clouds_id_area.values()))
        assert total_area_clouds - total_cloud_covered == cloud_uncovered

    def assert_resolution(self, selected_images, resolution):
        calculated_total_resolution = 0
        for element in range(len(self.instance.areas)):
            element_resolution = max(self.instance.resolution)
            for image in selected_images:
                if element in self.instance.images[image]:
                    if self.instance.resolution[image] < element_resolution:
                        element_resolution = self.instance.resolution[image]
            calculated_total_resolution += element_resolution
        assert calculated_total_resolution == resolution

    def assert_incidence_angle(self, selected_images, incidence_angle):
        max_incidence_angle = 0
        for image in selected_images:
            if self.instance.incidence_angle[image] > max_incidence_angle:
                max_incidence_angle = self.instance.incidence_angle[image]
        assert max_incidence_angle == incidence_angle