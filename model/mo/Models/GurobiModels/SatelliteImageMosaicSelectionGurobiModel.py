from gurobipy import max_

import gurobipy as gp

from model.mo.Models.GurobiModels.GurobiModel import GurobiModel
from model.mo.Models.SatelliteImageMosaicSelectionGeneralModel import SatelliteImageMosaicSelectionGeneralModel


class SatelliteImageMosaicSelectionGurobiModel(GurobiModel, SatelliteImageMosaicSelectionGeneralModel):

    def __init__(self, instance):
        self.elements = None
        self.areas = None
        self.images_id = None
        self.images, self.costs = None, None
        self.cloud_covered_by_image = None
        self.clouds_id, self.area_clouds = None, None
        self.resolution = None
        self.min_resolution = None
        self.incidence_angle = None
        SatelliteImageMosaicSelectionGeneralModel.__init__(self, instance)

    def is_numerically_possible_augment_objective(self):
        return False # For Ortools-cp it is not possible

    def create_model(self):
        return gp.Model("SIMSModel")

    def get_data_from_instance(self):
        self.elements, self.areas = gp.multidict({i: self.instance.areas[i] for i in range(len(self.instance.areas))})
        self.images_id, self.images, self.costs = gp.multidict({i: [self.instance.images[i], self.instance.costs[i]]
                                                                for i in range(len(self.instance.images))})
        # cloud processing
        self.cloud_covered_by_image = gp.tupledict(self.instance.cloud_covered_by_image)
        self.clouds_id, self.area_clouds = gp.multidict(self.instance.clouds_id_area)
        self.total_area_clouds = int(sum(self.area_clouds.values()))
        # resolution processing
        self.resolution = gp.tupledict(zip(self.images_id, self.instance.resolution))
        self.min_resolution = min(self.instance.resolution)
        # incidence angle processing
        self.incidence_angle = gp.tupledict(zip(self.images_id, self.instance.incidence_angle))
        # multiply to convert to integers


    def add_variables_to_model(self):
        # decision variables
        self.select_image = self.solver_model.addVars(len(self.images), vtype=gp.GRB.BINARY, name="select_image_i")
        self.cloud_covered = self.solver_model.addVars(self.clouds_id, vtype=gp.GRB.BINARY, name="cloud_covered_e")
        # support variables
        self.resolution_element = self.solver_model.addVars(self.elements, lb=self.min_resolution,
                                                            ub=max(self.resolution.values()), vtype=gp.GRB.INTEGER,
                                                            name="resolution_element_i")
        self.effective_image_resolution = self.solver_model.addVars(len(self.images), vtype=gp.GRB.INTEGER,
                                                                    name="effective_resolution_image_i")
        self.effective_incidence_angle = self.solver_model.addVars(len(self.images), vtype=gp.GRB.INTEGER,
                                                                   name="effective_incidence_angle_i")
        self.current_max_incidence_angle = self.solver_model.addVar(vtype=gp.GRB.INTEGER, name="max_allowed_incidence_angle")

    def define_objectives(self):
        # cost
        self.objectives.append(gp.quicksum(self.select_image[i] * self.costs[i] for i in self.images_id))
        # for cloud coverage
        self.objectives.append(
            self.total_area_clouds - (gp.quicksum(self.cloud_covered[c] * self.area_clouds[c]
                                                  for c in self.clouds_id)))
        # for resolution
        self.objectives.append(gp.quicksum(self.resolution_element[e] for e in self.elements))
        # for incidence angle
        self.objectives.append(self.current_max_incidence_angle)

    def add_constraints_to_model(self):
        # cover constraint
        self.constraints.append(self.solver_model.addConstrs(gp.quicksum(self.select_image[i] for i in self.images_id if e in self.images[i]) >= 1
                                     for e in self.elements))
        # cloud constraint
        self.constraints.append(self.solver_model.addConstrs(gp.quicksum(self.select_image[i] for i in self.cloud_covered_by_image.keys()
                                                 if c in self.cloud_covered_by_image[i]) >= self.cloud_covered[c]
                                     for c in self.clouds_id))
        self.constraints.append(self.solver_model.addConstrs(gp.quicksum(self.select_image[i] for i in self.cloud_covered_by_image.keys()
                                                 if c in self.cloud_covered_by_image[i]) <=
                                     self.cloud_covered[c] * len(self.images) for c in self.clouds_id))

        # calculate resolution for each element
        max_resolution = max(self.resolution.values())
        big_resolution = 2 * max_resolution
        self.constraints.append(self.solver_model.addConstrs(((self.select_image[i] == 0) >> (self.effective_image_resolution[i] == big_resolution)
                                      for i in self.images_id)))
        self.constraints.append(self.solver_model.addConstrs(((self.select_image[i] == 1) >> (self.effective_image_resolution[i] == self.resolution[i])
                                      for i in self.images_id)))
        self.constraints.append(self.solver_model.addConstrs(self.resolution_element[e] == gp.min_(self.effective_image_resolution[i] for i in
                                                                           self.images_id if e in self.images[i])
                                     for e in self.elements))
        # incidence angle constraint
        # The below approach using indicator constraints is faster than the one commented below
        self.constraints.append(self.solver_model.addConstrs(((self.select_image[i] == 0) >> (self.effective_incidence_angle[i] == 0)
                                      for i in self.images_id)))
        self.constraints.append(self.solver_model.addConstrs(
            ((self.select_image[i] == 1) >> (self.effective_incidence_angle[i] == self.incidence_angle[i])
             for i in self.images_id)))
        # Approach not using indicator constraints, it is slower than the one above
        # self.model.addConstrs(self.effective_incidence_angle[i] == self.select_image[i] * self.incidence_angle[i]
        #                       for i in self.images_id)
        self.constraints.append(self.solver_model.addConstr(self.current_max_incidence_angle == max_(self.effective_incidence_angle[i]
                                                                             for i in self.images_id)))
        # constraints end--------------------------------------------------------------

    def get_solution_values(self):
        selected_images = []
        for image in self.select_image.keys():
            if abs(self.select_image[image].x) > 1e-6:
                selected_images.append(image)
        return selected_images

    def add_necessary_solver_configuration(self):
        print("Extra solver configuration needed")
        self.solver_model.Params.IntegralityFocus = 1