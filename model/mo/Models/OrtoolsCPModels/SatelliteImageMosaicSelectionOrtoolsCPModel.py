import math

from ortools.sat.python import cp_model

from model.mo.Models.OrtoolsCPModels.OrtoolsCPModel import OrtoolsCPModel
from model.mo.Models.SatelliteImageMosaicSelectionGeneralModel import SatelliteImageMosaicSelectionGeneralModel


class SatelliteImageMosaicSelectionOrtoolsCPModel(OrtoolsCPModel, SatelliteImageMosaicSelectionGeneralModel):

    def __init__(self, instance):
        # variables
        self.cloud_area = None
        self.total_cost = None
        self.total_cloudy_area = None
        self.total_resolution = None
        # this variable has the current objective to optimize
        self.current_objective = None
        self.tackle_numerical_problems()
        OrtoolsCPModel.__init__(self)
        SatelliteImageMosaicSelectionGeneralModel.__init__(self, instance)

    def is_numerically_possible_augment_objective(self):
        return False

    def get_data_from_instance(self):
        self.total_area_clouds = int(sum(self.instance.clouds_id_area.values()))

    def add_variables_to_model(self):
        self.select_image = [self.solver_model.NewBoolVar(f"select_image{i}") for i in range(len(self.instance.images))]
        self.solution_variables.append(self.select_image)
        self.cloud_covered = {}
        self.cloud_area = {}
        for cloud in self.instance.clouds_id_area:
            self.cloud_covered[cloud] = self.solver_model.NewBoolVar(f"cloud_covered{cloud}")
            self.cloud_area[cloud] = self.solver_model.NewIntVar(0, self.instance.clouds_id_area[cloud], f"cloud_area{cloud}")

    def add_constraints_to_model(self):
        for i in range(len(self.instance.areas)):
            images_covering_element = self.get_images_covering_element(i)
            self.constraints.append(self.solver_model.AddAtLeastOne(self.select_image[j] for j in images_covering_element))

        for cloud in self.cloud_area:
            potential_images_covering_cloud = self.get_images_covering_cloud(cloud)
            for i in potential_images_covering_cloud:
                self.solver_model.Add(self.cloud_covered[cloud] == True).OnlyEnforceIf(self.select_image[i])
            self.constraints.append(self.solver_model.AddAtLeastOne(self.select_image[i] for i in potential_images_covering_cloud).OnlyEnforceIf(
                self.cloud_covered[cloud]))
            self.constraints.append(self.solver_model.Add(self.cloud_area[cloud] == 0).OnlyEnforceIf(self.cloud_covered[cloud]))
            self.constraints.append(self.solver_model.Add(self.cloud_area[cloud] == self.instance.clouds_id_area[cloud]).OnlyEnforceIf(
                self.cloud_covered[cloud].Not()))

    def define_objectives(self):
        # cost objective
        self.total_cost = self.solver_model.NewIntVar(0, sum(self.instance.costs), "cost")
        self.solver_model.Add(self.total_cost == sum(self.select_image[i] * self.instance.costs[i] for i in range(len(self.select_image))))
        self.objectives.append(self.total_cost)
        # cloud covered objective
        # todo try with model equivalent to minizinc, instead of covering the clouds, maximize the clean parts
        self.total_cloudy_area = self.solver_model.NewIntVar(0, self.total_area_clouds, "total_cloudy_area")
        self.solver_model.Add(self.total_cloudy_area == sum(self.cloud_area[i] for i in self.cloud_area))
        self.objectives.append(self.total_cloudy_area)

        # resolution objective
        max_total_resolution = max(self.instance.resolution) * len(self.instance.areas)
        self.total_resolution = self.solver_model.NewIntVar(0, max_total_resolution, "total_resolution")
        self.effective_image_resolution = [
            self.solver_model.NewIntVar(self.instance.resolution[i], max(self.instance.resolution) + 10,
                                 f"effective_resolution{i}") for i in
            range(len(self.instance.images))]
        for i in range(len(self.instance.images)):
            self.solver_model.Add(self.effective_image_resolution[i] == self.instance.resolution[i]).OnlyEnforceIf(
                self.select_image[i])
            self.solver_model.Add(self.effective_image_resolution[i] == max(self.instance.resolution) + 10).OnlyEnforceIf(
                self.select_image[i].Not())
        for i in range(len(self.instance.areas)):
            self.resolution_element.append(self.solver_model.NewIntVar(0, max(self.instance.resolution), f"resolution{i}"))
            images = self.get_images_covering_element(i)
            self.solver_model.AddMinEquality(self.resolution_element[i],
                                      [self.effective_image_resolution[ima] for ima in images])

        self.solver_model.Add(self.total_resolution == sum(self.resolution_element))
        self.objectives.append(self.total_resolution)

        # incidence angle objective
        self.current_max_incidence_angle = self.solver_model.NewIntVar(min(self.instance.incidence_angle),
                                                                max(self.instance.incidence_angle),
                                                                "max_incidence_angle")
        self.solver_model.AddMaxEquality(self.current_max_incidence_angle,
                                  [self.instance.incidence_angle[i] * self.select_image[i]
                                   for i in range(len(self.instance.images))])

        self.objectives.append(self.current_max_incidence_angle)

    def get_images_covering_element(self, element):
        return [i for i in range(len(self.instance.images)) if element in self.instance.images[i]]

    def get_images_covering_cloud(self, cloud):
        return [i for i in self.instance.cloud_covered_by_image if cloud in self.instance.cloud_covered_by_image[i]]


    def get_solution_values(self):
        selected_images = [index for index in range(len(self.select_image)) if
                           self.solver_values[index] == 1]
        return selected_images

    def tackle_numerical_problems(self):
        # self.instance.costs = [int(x/self.gcd(self.instance.costs)) for x in self.instance.costs]
        pass

    def gcd(self, list_to_gcd):
        gcd = list_to_gcd[0]
        for i in range(1, len(list_to_gcd)):
            gcd = math.gcd(gcd, list_to_gcd[i])
        return gcd

    def add_necessary_solver_configuration(self):
        print("Extra solver configuration no needed")