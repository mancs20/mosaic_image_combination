from abc import ABC, abstractmethod

import matplotlib.pyplot as plt
from geopandas import GeoDataFrame

import Experiment
import constants
import matplotlib.pyplot as plt
import contextily as cx

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
        # ax = Experiment.Experiment.config_plot_images_and_aoi(images=plot_results, aoi=self.original_aoi)

        #TODO delete this after tests
        # legend_column = "image_id"
        # images = plot_results
        # aoi = self.original_aoi
        # basemap = True
        # legend_elements = Experiment.Experiment.get_legend_elements(images, legend_column)
        # fig_size = (10, 10)
        # if len(legend_elements) > 0:
        #     colors = Experiment.Experiment.get_plot_colors(images)
        #     ax = images.plot(categorical=True,
        #                      figsize=fig_size,
        #                      legend=True,
        #                      alpha=0.7,
        #                      color=colors)
        #     ax.legend(handles=legend_elements, loc="upper left", bbox_to_anchor=(1, 1))
        # else:
        #     ax = images.plot(legend_column,
        #                      categorical=True,
        #                      figsize=fig_size,
        #                      legend=True,
        #                      alpha=0.7,
        #                      cmap="Set3",
        #                      legend_kwds=dict(loc="upper left", bbox_to_anchor=(1, 1)))
        # aoi.plot(color="r", ax=ax, fc="None", edgecolor="r", lw=1)
        # if basemap:
        #     cx.add_basemap(ax, crs=images.crs)
        # plt.show()

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
