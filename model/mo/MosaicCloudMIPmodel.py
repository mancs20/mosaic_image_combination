import gurobipy as gp
from gurobipy import max_


class MosaicCloudMIPmodel:

    def __init__(self, images, costs, areas, cloud_covered_by_image, clouds_id_area, max_cloud_area,
                 resolution, incidence_angle, model, multiply_to_convert_to_integers):
        self.model = model
        self.elements, self.areas = gp.multidict({i: areas[i] for i in range(len(areas))})
        self.images_id, self.images, self.costs = gp.multidict({i: [images[i], costs[i]] for i in range(len(images))})
        # cloud processing
        self.cloud_covered_by_image = gp.tupledict(cloud_covered_by_image)
        self.clouds_id, self.area_clouds = gp.multidict(clouds_id_area)
        # resolution processing
        self.resolution = gp.tupledict(zip(self.images_id, resolution))
        # incidence angle processing
        self.incidence_angle = gp.tupledict(zip(self.images_id, incidence_angle))
        # multiply to convert to integers
        self.multiply_to_convert_to_integers = multiply_to_convert_to_integers
        # variables
        self.select_image = None
        self.cloud_covered = None
        self.resolution_element = None
        self.effective_image_resolution = None
        self.effective_incidence_angle = None
        self.current_max_incidence_angle = None
        self.add_variables()
        # self.cost_objective = None
        # self.cloud_objective = None
        # self.incidence_angle_objective = None
        # self.resolution_objective = None
        self.objectives = []
        self.add_objectives()

    def add_variables(self):
        # decision variables
        self.select_image = self.model.addVars(len(self.images), vtype=gp.GRB.BINARY, name="select_image_i")
        self.cloud_covered = self.model.addVars(self.clouds_id, vtype=gp.GRB.BINARY, name="cloud_covered_e")
        # support variables
        self.resolution_element = self.model.addVars(self.elements, vtype=gp.GRB.CONTINUOUS,
                                                     name="resolution_element_i")
        self.effective_image_resolution = self.model.addVars(len(self.images), vtype=gp.GRB.CONTINUOUS,
                                                        name="effective_resolution_element_i")
        self.effective_incidence_angle = self.model.addVars(len(self.images), vtype=gp.GRB.CONTINUOUS,
                                                       name="effective_incidence_angle_i")
        self.current_max_incidence_angle = self.model.addVar(vtype=gp.GRB.CONTINUOUS,
                                                             name="max_allowed_incidence_angle")

    def optimize_e_constraint(self, range_array):
        obj = self.get_main_objective()
        delta = 0.001 # delta between 0.001 and 0.000001
        rest_obj = self.objectives[0]/range_array[0]
        # for from 1 to range of self.objectives
        for i in range(1, len(self.objectives)):
            rest_obj = rest_obj + (self.objectives[i]/range_array[i])
        obj = obj + (delta * rest_obj)
        self.model.setObjective(obj)

    def get_main_objective(self):
        return gp.quicksum(self.select_image[i] * self.costs[i] for i in self.images_id)

    def add_objectives(self):
        # self.objectives.append(gp.quicksum(self.select_image[i] * self.costs[i] for i in self.images_id))
        # for cloud coverage
        # TODO maybe it will be good to convert the objectives to integers, this could be done multiplying by 10 in some
        # cases like the resolution and maybe incidence angle or rounding in the case of the cloud coverage
        self.objectives.append((gp.quicksum(self.area_clouds[c] for c in self.clouds_id) - \
                          gp.quicksum(self.cloud_covered[c] * self.area_clouds[c] for c in self.clouds_id)) *
                               self.multiply_to_convert_to_integers)
        # for resolution
        self.objectives.append(gp.quicksum(self.resolution_element[e] for e in self.elements) *
                               self.multiply_to_convert_to_integers)
        # for incidence angle
        self.objectives.append(self.current_max_incidence_angle * self.multiply_to_convert_to_integers)

    def add_basic_constraints(self):
        max_resolution = max(self.resolution.values())
        big_resolution = 2 * max_resolution
        # cost constraint
        self.model.addConstrs(gp.quicksum(self.select_image[i] for i in self.images_id if e in self.images[i]) >= 1
                              for e in self.elements)
        # cloud constraint
        self.model.addConstrs(gp.quicksum(self.select_image[i] for i in self.cloud_covered_by_image.keys()
                                          if c in self.cloud_covered_by_image[i]) >= self.cloud_covered[c]
                                            for c in self.clouds_id)
        # calculate resolution for each element
        self.model.addConstrs(((self.select_image[i] == 0) >> (self.effective_image_resolution[i] == big_resolution)
                               for i in self.images_id))
        self.model.addConstrs(((self.select_image[i] == 1) >> (self.effective_image_resolution[i] == self.resolution[i])
                               for i in self.images_id))
        self.model.addConstrs(self.resolution_element[e] == gp.min_(self.effective_image_resolution[i] for i in
                                                                    self.images_id if e in self.images[i])
                                                                    for e in self.elements)
        # incidence angle constraint
        self.model.addConstrs(((self.select_image[i] == 0) >> (self.effective_incidence_angle[i] == 0)
                               for i in self.images_id))
        self.model.addConstrs(((self.select_image[i] == 1) >> (self.effective_incidence_angle[i] == self.incidence_angle[i])
                               for i in self.images_id))
        # self.model.addConstrs(self.effective_incidence_angle[i] == self.select_image[i] * self.incidence_angle[i]
        #                       for i in self.images_id)
        self.model.addConstr(self.current_max_incidence_angle == max_(self.effective_incidence_angle[i]
                                                                      for i in self.images_id))
        # constraints end--------------------------------------------------------------

    def add_objective_constraints(self, ef_array):
        for i in range(len(self.objectives)):
            self.model.addConstr(self.objectives[i] <= ef_array[i])


    # def add_basic_constraints(self):
    #     max_resolution = max(self.resolution.values())
    #     big_resolution = 2 * max_resolution
    #     model_add_constraints(model, images, images_id, elements, clouds_id, cloud_covered_by_image, resolution,
    #                                   big_resolution)
    #
    #     # # multiobjective constraint with epsilon approach
    #     # # for cloud coverage
    #     model.addConstr(gp.quicksum(area_clouds[c] for c in clouds_id) - gp.quicksum(
    #         cloud_covered[c] * area_clouds[c] for c in clouds_id) <= max_cloud_area)
    #     # # for resolution
    #     model.addConstr(gp.quicksum(resolution_element[e] for e in elements) <= max_resolution * len(elements))
    #     # # for incidence angle
    #     model.addConstrs(effective_incidence_angle[i] == select_image[i] * incidence_angle[i] for i in images_id)
    #     model.addConstr(current_max_incidence_angle == max_(effective_incidence_angle[i] for i in images_id))
    #     model.addConstr(current_max_incidence_angle <= max_incidence_angle)

    # def model_add_constraints(self, model, images, images_id, elements, clouds_id, cloud_covered_by_image, resolution,
    #                           big_resolution):



