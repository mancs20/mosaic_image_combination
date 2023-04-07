import copy

from geopandas import GeoDataFrame

from Strategies.Strategy import Strategy
from abc import abstractmethod


class StrategyDiscrete(Strategy):
    def __init__(self):
        super().__init__()
        self.contained_images = None
        self.sets_images = []
        self.universe = []

    @abstractmethod
    def run_strategy(self):
        pass

    def discretize(self):
        self.remove_image_area_outside_aoi()
        self.sets_images = self.discretize_brute_force()

    def remove_image_area_outside_aoi(self):
        intersection_images_aoi = self.images.intersection(self.aoi.unary_union)
        self.contained_images = self.images.set_geometry(intersection_images_aoi)
