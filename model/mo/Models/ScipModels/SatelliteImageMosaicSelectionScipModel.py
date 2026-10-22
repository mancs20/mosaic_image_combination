from pyscipopt import Model, quicksum

from model.mo.Models.ScipModels.ScipModel import ScipModel
from model.mo.Models.SatelliteImageMosaicSelectionGeneralModel import SatelliteImageMosaicSelectionGeneralModel


class SatelliteImageMosaicSelectionScipModel(ScipModel, SatelliteImageMosaicSelectionGeneralModel):
    """Same model as SatelliteImageMosaicSelectionGurobiModel. SCIP has no max general constraint and its indicator
    constraints only take inequalities, so the incidence angle is modelled with linear constraints (see
    add_incidence_angle_constraints)."""

    def __init__(self, instance):
        self.auxiliary_variables_for_resolution = []
        self.images_covering_element = None
        self.elements = None
        self.areas = None
        self.images_id = None
        self.images, self.costs = None, None
        self.cloud_covered_by_image = None
        self.clouds_id, self.area_clouds = None, None
        self.resolution = None
        self.min_resolution = None
        self.incidence_angle = None
        self.image_with_max_incidence_angle = None
        SatelliteImageMosaicSelectionGeneralModel.__init__(self, instance)

    def is_numerically_possible_augment_objective(self):
        return True

    # nadir and reference points: same values as SatelliteImageMosaicSelectionGurobiModel ---------------------------
    def get_nadir_bound_estimation(self):
        return [self.get_nadir_of_objective(objective) for objective in self.instance.active_objectives]

    def get_ref_points_for_hypervolume(self):
        return [self.get_ref_point_of_objective(objective) for objective in self.instance.active_objectives]

    def get_nadir_of_objective(self, objective):
        if objective == "cost":
            return sum(self.instance.costs)
        if objective == "clouds":
            return sum(self.instance.areas)
        if objective == "resolution":
            return self.get_resolution_nadir_for_ref_point()
        return max(self.instance.incidence_angle)

    def get_ref_point_of_objective(self, objective):
        if objective == "incidence_angle":
            return 900
        return self.get_nadir_of_objective(objective) + 1
    # ---------------------------------------------------------------------------------------------------------------

    def create_model(self):
        return Model("SIMSModel")

    def get_data_from_instance(self):
        self.elements = list(range(len(self.instance.areas)))
        self.areas = {e: self.instance.areas[e] for e in self.elements}
        self.images_id = list(range(len(self.instance.images)))
        self.images = {i: self.instance.images[i] for i in self.images_id}
        self.costs = {i: self.instance.costs[i] for i in self.images_id}
        # cloud processing
        self.cloud_covered_by_image = self.instance.cloud_covered_by_image
        self.clouds_id = list(self.instance.clouds_id_area.keys())
        self.area_clouds = self.instance.clouds_id_area
        self.total_area_clouds = int(sum(self.area_clouds.values()))
        if self.has_objective("resolution"):
            self.resolution = dict(zip(self.images_id, self.instance.resolution))
            self.min_resolution = min(self.instance.resolution)
            self.images_covering_element = {}
            for i in self.images_id:
                for e in self.images[i]:
                    self.images_covering_element.setdefault(e, []).append(i)
        if self.has_objective("incidence_angle"):
            self.incidence_angle = dict(zip(self.images_id, self.instance.incidence_angle))

    def has_objective(self, objective_name):
        # Only the objectives that are present in the instance data are part of the model (see InstanceSIMS)
        return objective_name in self.instance.active_objectives

    def add_variables_to_model(self):
        # decision variables
        self.select_image = {i: self.solver_model.addVar(vtype="B", name=f"select_image_{i}") for i in self.images_id}
        self.cloud_covered = {c: self.solver_model.addVar(vtype="B", name=f"cloud_covered_{c}")
                              for c in self.clouds_id}
        # support variables
        if self.has_objective("resolution"):
            self.resolution_element = {e: self.solver_model.addVar(vtype="I", lb=self.min_resolution,
                                                                   ub=max(self.resolution.values()),
                                                                   name=f"resolution_element_{e}")
                                       for e in self.elements}
            self.auxiliary_variables_for_resolution = [0] * len(self.elements)
            for element in self.elements:
                self.auxiliary_variables_for_resolution[element] = {}
                for image in self.images_covering_element[element]:
                    self.auxiliary_variables_for_resolution[element][image] = self.solver_model.addVar(
                        vtype="B", name=f"auxiliary_variable_for_resolution{element}_{image}")
        if self.has_objective("incidence_angle"):
            max_angle = max(self.incidence_angle.values())
            self.effective_incidence_angle = {i: self.solver_model.addVar(vtype="I", lb=0, ub=max_angle,
                                                                          name=f"effective_incidence_angle_{i}")
                                              for i in self.images_id}
            self.current_max_incidence_angle = self.solver_model.addVar(vtype="I", lb=0, ub=max_angle,
                                                                        name="max_allowed_incidence_angle")
            # image_with_max_incidence_angle[i] = 1 for one image whose effective angle is the max
            self.image_with_max_incidence_angle = {i: self.solver_model.addVar(vtype="B",
                                                                               name=f"image_with_max_angle_{i}")
                                                   for i in self.images_id}

    def define_objectives(self):
        # cost
        self.objectives.append(quicksum(self.select_image[i] * self.costs[i] for i in self.images_id))
        # for cloud coverage
        self.objectives.append(self.total_area_clouds - quicksum(self.cloud_covered[c] * self.area_clouds[c]
                                                                 for c in self.clouds_id))
        # for resolution
        if self.has_objective("resolution"):
            self.objectives.append(quicksum(self.resolution_element[e] for e in self.elements))
        # for incidence angle
        if self.has_objective("incidence_angle"):
            self.objectives.append(self.current_max_incidence_angle)

    def review_objective_values(self, objective_values):
        # as in the Gurobi model, the resolution value is calculated manually from the selected images
        selected_images = self.get_solution_values()
        if self.has_objective("resolution"):
            objective_values[self.instance.active_objectives.index("resolution")] = \
                self.calculate_resolution(selected_images)

    def add_constraints_to_model(self):
        # cover constraint
        for e in self.elements:
            self.constraints.append(self.solver_model.addCons(
                quicksum(self.select_image[i] for i in self.images_id if e in self.images[i]) >= 1))
        # cloud constraint
        for c in self.clouds_id:
            images_covering_cloud = quicksum(self.select_image[i] for i in self.cloud_covered_by_image.keys()
                                             if c in self.cloud_covered_by_image[i])
            self.constraints.append(self.solver_model.addCons(images_covering_cloud >= self.cloud_covered[c]))
            self.constraints.append(self.solver_model.addCons(images_covering_cloud <=
                                                              self.cloud_covered[c] * len(self.images)))
        # calculate resolution for each element
        if self.has_objective("resolution"):
            big_resolution = max(self.resolution.values()) + 1
            for element in self.elements:
                total_auxiliary_variables = len(self.auxiliary_variables_for_resolution[element])
                self.constraints.append(self.solver_model.addCons(
                    quicksum(self.auxiliary_variables_for_resolution[element][i]
                             for i in self.auxiliary_variables_for_resolution[element]) ==
                    total_auxiliary_variables - 1, name=f"constraint_auxiliary_variables_for_resolution{element}"))
            for e in self.elements:
                for i in self.images_id:
                    if e in self.images[i]:
                        self.constraints.append(self.solver_model.addCons(
                            self.resolution_element[e] >= self.resolution[i] * self.select_image[i] +
                            big_resolution * (1 - self.select_image[i]) -
                            2 * big_resolution * self.auxiliary_variables_for_resolution[e][i]))
        if self.has_objective("incidence_angle"):
            self.add_incidence_angle_constraints()

    def add_incidence_angle_constraints(self):
        # effective angle of an image: its angle if it is selected, 0 if not (the Gurobi model uses two indicator
        # constraints, it is a linear equality because select_image is binary)
        for i in self.images_id:
            self.constraints.append(self.solver_model.addCons(
                self.effective_incidence_angle[i] == self.incidence_angle[i] * self.select_image[i]))
        # current_max_incidence_angle == max of the effective angles (max_ in the Gurobi model): it is at least each
        # effective angle, and at most the effective angle of the image chosen by image_with_max_incidence_angle
        big_m = max(self.incidence_angle.values())
        for i in self.images_id:
            self.constraints.append(self.solver_model.addCons(
                self.current_max_incidence_angle >= self.effective_incidence_angle[i]))
            self.constraints.append(self.solver_model.addCons(
                self.current_max_incidence_angle <= self.effective_incidence_angle[i] +
                big_m * (1 - self.image_with_max_incidence_angle[i])))
        self.constraints.append(self.solver_model.addCons(
            quicksum(self.image_with_max_incidence_angle[i] for i in self.images_id) == 1))

    def get_solution_values(self):
        return [image for image in self.images_id if self.is_selected(self.select_image[image])]

    def add_necessary_solver_configuration(self):
        print("Extra solver configuration no needed")
