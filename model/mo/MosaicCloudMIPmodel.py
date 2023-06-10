import gurobipy as gp
from gurobipy import max_


class MosaicCloudMIPmodel:

    def __init__(self, images, costs, areas, cloud_covered_by_image, clouds_id_area, max_cloud_area,
                 resolution, incidence_angle, model):
        self.model = model
        self.elements, self.areas = gp.multidict({i: areas[i] for i in range(len(areas))})
        self.images_id, self.images, self.costs = gp.multidict({i: [images[i], costs[i]] for i in range(len(images))})
        # cloud processing
        self.cloud_covered_by_image = gp.tupledict(cloud_covered_by_image)
        self.clouds_id, self.area_clouds = gp.multidict(clouds_id_area)
        self.total_area_clouds = sum(self.area_clouds.values())
        # resolution processing
        self.resolution = gp.tupledict(zip(self.images_id, resolution))
        # incidence angle processing
        self.incidence_angle = gp.tupledict(zip(self.images_id, incidence_angle))
        # multiply to convert to integers
        # variables
        self.select_image = None
        self.cloud_covered = None
        self.resolution_element = None
        self.effective_image_resolution = None
        self.effective_incidence_angle = None
        self.current_max_incidence_angle = None
        self.add_variables()
        self.objectives = []
        self.add_objectives()
        self.constraint_objectives = [0] * len(self.objectives)

    def add_variables(self):
        # decision variables
        self.select_image = self.model.addVars(len(self.images), vtype=gp.GRB.BINARY, name="select_image_i")
        # self.cloud_covered = self.model.addVars(self.clouds_id, vtype=gp.GRB.BINARY, name="cloud_covered_e")
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
        # TODO: initially try withouth delta
        # obj = obj + (delta * rest_obj)
        self.model.setObjective(obj)

    def get_main_objective(self):
        return gp.quicksum(self.select_image[i] * self.costs[i] for i in self.images_id)

    def add_objectives(self):
        # for cloud coverage
        # self.objectives.append(-(gp.quicksum(self.cloud_covered[c] * self.area_clouds[c] for c in self.clouds_id)))
        # for resolution
        self.objectives.append(gp.quicksum(self.resolution_element[e] for e in self.elements))
        # for incidence angle
        self.objectives.append(self.current_max_incidence_angle)

    def add_basic_constraints(self):
        max_resolution = max(self.resolution.values())
        big_resolution = 2 * max_resolution
        # cost constraint
        self.model.addConstrs(gp.quicksum(self.select_image[i] for i in self.images_id if e in self.images[i]) >= 1
                              for e in self.elements)
        # cloud constraint
        # self.model.addConstrs(gp.quicksum(self.select_image[i] for i in self.cloud_covered_by_image.keys()
        #                                   if c in self.cloud_covered_by_image[i]) >= self.cloud_covered[c]
        #                                     for c in self.clouds_id)
        # self.model.addConstrs(gp.quicksum(self.select_image[i] for i in self.cloud_covered_by_image.keys()
        #                                   if c in self.cloud_covered_by_image[i]) <=
        #                       self.cloud_covered[c] * len(self.images) for c in self.clouds_id)

        # calculate resolution for each element
        self.model.addConstrs(((self.select_image[i] == 0) >> (self.effective_image_resolution[i] == big_resolution)
                               for i in self.images_id))
        self.model.addConstrs(((self.select_image[i] == 1) >> (self.effective_image_resolution[i] == self.resolution[i])
                               for i in self.images_id))
        self.model.addConstrs(self.resolution_element[e] == gp.min_(self.effective_image_resolution[i] for i in
                                                                    self.images_id if e in self.images[i])
                                                                    for e in self.elements)
        # incidence angle constraint
        # The below approach using indicator constraints is faster than the one commented below
        self.model.addConstrs(((self.select_image[i] == 0) >> (self.effective_incidence_angle[i] == 0)
                               for i in self.images_id))
        self.model.addConstrs(((self.select_image[i] == 1) >> (self.effective_incidence_angle[i] == self.incidence_angle[i])
                               for i in self.images_id))
        # Approach not using indicator constraints, it is slower than the one above
        # self.model.addConstrs(self.effective_incidence_angle[i] == self.select_image[i] * self.incidence_angle[i]
        #                       for i in self.images_id)
        self.model.addConstr(self.current_max_incidence_angle == max_(self.effective_incidence_angle[i]
                                                                      for i in self.images_id))
        # constraints end--------------------------------------------------------------

    def add_objective_constraints(self, ef_array):
        for i in range(len(self.objectives)):
            # self.constraint_objectives[i] = self.model.addConstr(self.objectives[i] <= ef_array[i])
            self.constraint_objectives[i] = self.model.addConstr(self.objectives[i] <= ef_array[i])

    def update_objective_constraints(self, ef_array):
        for i in range(len(ef_array)):
            self.model.setAttr(gp.GRB.Attr.RHS, self.constraint_objectives[i], ef_array[i])
