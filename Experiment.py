import json
import os
import re
from abc import ABC, abstractmethod
import geopandas
from geopandas import GeoDataFrame
import pandas as pd
import up42
import matplotlib.pyplot as plt
import ProjectDataClasses
from Strategies import IStrategy
from DataMarketPlaces import Marketplace
from typing import List

DATA_FILE_NAME_CSV = '20images_data.csv'
DATA_FILE_NAME = '20images_data.geojson'
COVERAGE_IMAGE_NAME = 'coverage.png'


class Experiment(ABC):
    def __init__(self, aoi_file, search_parameters: ProjectDataClasses.SearchParameters):
        self.marketplace = None
        self.strategy: IStrategy = None
        processed_aoi_file = up42.read_vector_file(aoi_file)
        self.aoi: GeoDataFrame = geopandas.GeoDataFrame.from_features(processed_aoi_file)
        self.search_parameters = search_parameters
        self.search_parameters.aoi = processed_aoi_file
        self.images: Union[GeoDataFrame, dict] = None
        self.folder_experiment_results = ""
        self.working_dir = ""
        self.check_create_working_dir(aoi_file)

    def set_marketplace(self, marketplace: Marketplace):
        self.marketplace = marketplace

    def prepare_experiment(self):
        # Create or get folder for experiment results
        if not self.check_if_local_data():
            self.images = self.marketplace.get_data_from_marketplace()
            if not self.is_aoi_covered_by_searched_images():
                return False
            # TODO uncomment below after doing the random experiments and see they are different enough
            # self.images = self.marketplace.update_images_cost()
            self.save_data()
        else:
            self.images = geopandas.read_file(self.working_dir + '/' + DATA_FILE_NAME)
            self.config_plot_images_and_aoi(self.images)
        plt.show()
        return True

    def check_create_working_dir(self, aoi_file):
        current_dir = os.path.dirname(__file__)
        dir_name = re.search('/(.*).geojson', aoi_file).group(1)
        self.working_dir = os.path.join(current_dir, 'results', dir_name)
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

    def check_if_local_data(self):
        return os.path.exists(self.working_dir + '/' + DATA_FILE_NAME)

    def is_aoi_covered_by_searched_images(self):
        all_images_union = self.images.unary_union  # convert all images (GeoSeries) in a single polygon
        # check if GeoDataFrame is inside a Polygon
        if len(self.aoi.within(all_images_union)) == 0:
            print("The images are not covering the whole aoi, try another search")
            return False
        else:
            return True
        pass

    def save_data(self):
        # save data to csv, human readable
        self.images.to_csv(self.working_dir + '/' + DATA_FILE_NAME_CSV, index_label='image_id')
        # save to geojson, remove fields with lists, for shp is the same
        images_without_list_fields = self.marketplace.prepare_data_to_save(self.images)
        images_without_list_fields.to_file(self.working_dir + '/' + DATA_FILE_NAME, driver='GeoJSON')
        self.save_search_parameters()
        self.config_plot_images_and_aoi(self.images)
        self.save_coverage_image(self.working_dir, COVERAGE_IMAGE_NAME)

    def save_search_parameters(self):
        params_json = self.marketplace.convert_search_parameters_without_aoi_to_json()
        file_name = self.working_dir + '/search_parameters.json'
        with open(file_name, 'w') as outfile:
            outfile.write(json.dumps(params_json))

    @staticmethod
    def save_coverage_image(path, image_name):
        plt.savefig(path + '/' + image_name)

    def config_plot_images_and_aoi(self, images, legend_column="image_id"):
        # TODO change this function to save images with the 20 specifics colors there are in constants.py
        fig_size = (12, 16)
        ax = images.plot(legend_column,
                         categorical=True,
                         figsize=fig_size,
                         cmap="Set3",
                         legend=True,
                         alpha=0.7,
                         legend_kwds=dict(loc="upper left", bbox_to_anchor=(1, 1)), )
        self.aoi.plot(color="r", ax=ax, fc="None", edgecolor="r", lw=1)
        ax.set_axis_off()
        # plt.show()

    def set_strategy(self, strategy: IStrategy):
        self.strategy = strategy
        # create strategy folder
        folder_strategy = self.working_dir + '/' + strategy.name
        if not os.path.exists(folder_strategy):
            os.makedirs(folder_strategy)
        self.strategy.path = folder_strategy

    def run_experiment(self, aoi, images):
        selected_images_results = []
        for i in range(self.strategy.number_of_runs):
            selected_images_results.append(self.strategy.run_strategy(aoi, images))
        # Process results
        self.proccess_results(selected_images_results)
        # Save results
        self.save_results(selected_images_results)

    def process_results(self, selected_images_results):
        # TODO write code
        a = 10

    def save_results(self, selected_images_results: List):
        # TODO write code
        # for results in selected_images_results:
        a = 10
