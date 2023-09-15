from numpy import random

import constants
from Strategies.StrategyDiscrete.StrategyDiscrete import StrategyDiscrete
from Strategies.StrategyDiscrete.SolverMinizinc import SolverMinizinc


class CPClouds(StrategyDiscrete, SolverMinizinc):
    path = ""
    name = "Constraint_Programming_Discrete_With_Clouds"
    number_of_runs = 1

    @property
    def model_path(self):
        return "../../model/mosaic_cloud2.mzn"

    def __init__(self, clouds:constants.Clouds, max_cloud_cover=0.2):
        super().__init__()
        self.with_clouds = True
        self.cloud_name = clouds.value
        self.name = "Discrete_Constraint_Programming_" + self.cloud_name
        if clouds.name == clouds.NO_CLOUDS.name:
            self.with_clouds = False
        self.clouds = []
        self.areas = []
        self.max_cloud_cover = max_cloud_cover

    def run_strategy(self):
        dzn_filename = SolverMinizinc.dzn_filename(self.aoi.iloc[0]["name"], len(self.images),
                                                   cloud_name=self.cloud_name)
        dzn_file_exists = SolverMinizinc.dzn_file_exists(dzn_filename)
        results = self.initialize_result()
        if not dzn_file_exists:
            super().discretize()
            if self.with_clouds:
                self.deal_with_clouds()
            minizinc_parameters = self.solver_minizinc_parameters()
            # TODO set this to False after saving the dzn files
            just_save_dzn_file = True
            if just_save_dzn_file:
                print("*************************************Saving dzn file name:" + dzn_filename+"*************************************")
                SolverMinizinc.write_dzn_file(dzn_filename, minizinc_parameters)
            else:
                results = self.get_transformed_solutions(results=results, images=self.images, sets_images=self.sets_images,
                                                     universe=self.universe,
                                                     minizinc_parameters=minizinc_parameters)
        else:
            # TODO set this to False after processing the dzn file
            modify_dzn_file = False
            if modify_dzn_file:
                self.modify_dzn_file(dzn_filename)
            else:
                # TODO uncomment below to get results from minizinc
                #----------------------------------------------
                a = 2
        return self.prepare_results_to_return(results)



    def solver_minizinc_parameters(self) -> dict:
        solver_parameters = {"num_images": len(self.sets_images),
                             "universe": self.universe,
                             "images": self.get_image_sets(),
                             "costs": [x.weight for x in self.sets_images],
                             "resolution": [x.resolution for x in self.sets_images],
                             "incidence_angle": [x.incidence_angle for x in self.sets_images]}
        if self.with_clouds:
            solver_parameters = self.add_clouds_to_solver_parameters(solver_parameters)
        return solver_parameters

    def add_clouds_to_solver_parameters(self, solver_parameters: dict) -> dict:
        solver_parameters["clouds"] = self.clouds
        solver_parameters["areas"] = self.areas
        max_cloud_area = self.calculate_max_cloud_cover_area()
        solver_parameters["max_cloud_area"] = max_cloud_area
        return solver_parameters

    def get_results_from_cp_solver(self, minizinc_parameters: dict = None):
        results = self.initialize_result()
        results = self.get_transformed_solutions(results=results, images=self.images, sets_images=self.sets_images,
                                                 universe=self.universe,
                                                 minizinc_parameters=minizinc_parameters)
        return self.prepare_results_to_return(results)

    def get_image_sets(self):
        sets = []
        for x in self.sets_images:
            regions_ids = []
            for region in x.list_of_regions:
                regions_ids.append(region.id)
            sets.append(set(regions_ids))
        return sets

    def deal_with_clouds(self):
        self.detect_clouds()
        self.build_cloud_sets_from_penalized_regions()
        self.build_area_array()

    def detect_clouds(self):
        # TODO detect clouds
        for image in self.sets_images:
            row = self.contained_images[self.contained_images["image_id"] == image.image_id]
            area = row.area.iloc[0]
            cloudy_area = row.iloc[0]["cloudCoverage"] / 100 * area
            cloud_regions_area = 0
            list_of_regions_id = list(range(len(image.list_of_regions)))
            if cloudy_area != 0:
                while len(list_of_regions_id) > 0 and 0.9 * cloudy_area > cloud_regions_area:
                    # region is a random number from the list_of_regions_id
                    region = random.choice(list_of_regions_id)
                    # add the area of the region to the cloud_regions_area
                    if cloud_regions_area + image.list_of_regions[region].area < 1.1 * cloudy_area:
                        cloud_regions_area += image.list_of_regions[region].area
                        image.list_of_regions[region].penalized = True
                    # remove the region from the list
                    list_of_regions_id.remove(region)

    def build_cloud_sets_from_penalized_regions(self):
        for image in self.sets_images:
            cloud_set = set()
            # cloud_set.add(self.universe + 1)
            for region in image.list_of_regions:
                if region.penalized:
                    cloud_set.add(region.id)
            # check if the cloud set is not empty
            if len(cloud_set) == 0:
                cloud_set = {}
            self.clouds.append(cloud_set)

    def build_area_array(self):
        region_already_added_set = set()
        for image in self.sets_images:
            for region in image.list_of_regions:
                if region.id not in region_already_added_set:
                    region_already_added_set.add(region.id)
                    self.areas.append(region.area)

    def calculate_max_cloud_cover_area(self):
        return self.aoi.area.iloc[0] * self.max_cloud_cover

    def modify_dzn_file(self, dzn_filename):
        print("***************Modifying dzn file***************")
        print("File name: " + dzn_filename)
        print("*************************************************")
        # build the sets of images
        self.remove_image_area_outside_aoi()
        self.initialize_set_images()

        # add parameters to the dzn file
        extraparameters = {'resolution': [x.resolution for x in self.sets_images],
                           "incidence_angle": [x.incidence_angle for x in self.sets_images]}
        SolverMinizinc.add_new_parameter_to_dzn_file(dzn_filename, extraparameters)

