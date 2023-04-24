from numpy import random
from Strategies.StrategyDiscrete.CPWithouyClouds import CPWithoutClouds


class CPClouds(CPWithoutClouds):
    path = ""
    name = "Constraint_Programming_Discrete_With_Clouds"
    number_of_runs = 1

    @property
    def model_path(self):
        return "./model/mosaic_cloud.mzn"

    def __init__(self, max_cloud_cover=0.2):
        super().__init__()
        self.clouds = []
        self.areas = []
        self.max_cloud_cover = max_cloud_cover

    def run_strategy(self):
        super().discretize()
        self.deal_with_clouds()
        return self.get_results_from_cp_solver()

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
            for region in image.list_of_regions:
                if region.penalized:
                    cloud_set.add(region.id)
            self.clouds.append(cloud_set)

    def build_area_array(self):
        region_already_added_set = set()
        for image in self.sets_images:
            for region in image.list_of_regions:
                if region.id not in region_already_added_set:
                    region_already_added_set.add(region.id)
                    self.areas.append(region.area)

    def initialize_model_parameters(self, instance):
        super().initialize_model_parameters(instance)
        # TODO add the cloud parameters
        # instance["clouds"] = self.clouds
        # instance["areas"] = self.areas
        # instance["max_cloud_area"] = self.calculate_max_cloud_cover_area

    def calculate_max_cloud_cover_area(self):
        return self.aoi.area.iloc[0] * self.max_cloud_cover