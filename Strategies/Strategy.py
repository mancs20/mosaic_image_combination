from abc import ABC, abstractmethod

import matplotlib.pyplot as plt
from geopandas import GeoDataFrame

import Experiment
import constants
import matplotlib.pyplot as plt

class Strategy(ABC):
    # noinspection PyTypeChecker
    def __init__(self):
        self.aoi: GeoDataFrame = None
        self.original_aoi: GeoDataFrame = None
        self.images: GeoDataFrame = None
        self.original_projection: int = None

    @abstractmethod
    def run_strategy(self):
        pass

    def initialize_result(self):
        return self.images[self.images.geom_type != "Polygon"]

    def update_results_and_aoi(self, image_id: int, results: GeoDataFrame):
        selected_image = self.images.loc[image_id]
        results = results.append(selected_image)
        # Update the area of interest, aoi subtracting the new image, the result is a new polygon
        self.aoi = self.aoi.difference(selected_image.geometry)
        self.images = self.images.drop(image_id)
        return results

    def prepare_strategy(self, aoi, images):
        self.aoi = aoi
        self.original_aoi = aoi
        self.images = images
        self.change_projection_to_planar_crs()

    def change_projection_to_planar_crs(self, crs=constants.PLANAR_CRS):
        self.original_projection = self.images.crs
        self.aoi = self.aoi.to_crs(crs)
        self.images = self.images.to_crs(crs)

    def prepare_results_to_return(self, results):
        results = self.change_projection_to_original(results)
        return results

    def change_projection_to_original(self, results):
        results.crs = self.images.crs
        temp_result = results.to_crs(self.original_projection)
        results.crs = None
        return temp_result

    def print_temp_results(self, results):
        plot_results = self.change_projection_to_original(results)
        ax = Experiment.Experiment.config_plot_images_and_aoi(plot_results, self.original_aoi)
        plt.show()

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def path(self):
        pass

    @property
    @abstractmethod
    def number_of_runs(self):
        pass
