import json
import os
import re
from abc import ABC, abstractmethod
import geopandas
from geopandas import GeoDataFrame
import pandas as pd
import up42
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import ProjectDataClasses
from Strategies import Strategy
from DataMarketPlaces import Marketplace
from typing import List
import constants
import numpy as np
import csv
from dataclasses import dataclass, fields, asdict

DATA_FILE_NAME_CSV = '20images_data.csv'
DATA_FILE_NAME = '20images_data.geojson'
COVERAGE_IMAGE_NAME = 'coverage.png'
EXPERIMENT_RESULTS_FILE = 'experiment_results.csv'
EXPERIMENT_RESULTS_COVERAGE = 'experiment_result_coverage_'


class Experiment(ABC):
    def __init__(self, aoi_file, search_parameters: ProjectDataClasses.SearchParameters):
        self.marketplace = None
        self.strategy: Strategy = None
        processed_aoi_file = up42.read_vector_file(aoi_file)
        self.aoi: GeoDataFrame = geopandas.GeoDataFrame.from_features(processed_aoi_file)
        self.search_parameters = search_parameters
        self.search_parameters.aoi = processed_aoi_file
        self.images: Union[GeoDataFrame, dict] = None
        self.processed_results = []
        self.selected_images_results = []
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
            # TODO uncomment below to get images marketplace cost
            # self.images = self.marketplace.update_images_cost()
            self.save_data()
        else:
            self.images = geopandas.read_file(self.working_dir + '/' + DATA_FILE_NAME)
            self.config_plot_images_and_aoi(self.images)
        plt.show()
        # set aoi with the same crs (projection system) as the images
        self.aoi.crs = self.images.crs
        self.aoi.to_crs(self.aoi.crs)
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
        legend_elements = self.get_legend_elements(images, legend_column)
        colors = self.get_plot_colors(images)
        fig_size = (12, 16)
        ax = images.plot(categorical=True,
                         figsize=fig_size,
                         legend=True,
                         alpha=0.7,
                         color=colors)
        self.aoi.plot(color="r", ax=ax, fc="None", edgecolor="r", lw=1)
        ax.legend(handles=legend_elements, loc="upper left", bbox_to_anchor=(1, 1))
        # ax.set_axis_off()

    @staticmethod
    def get_plot_colors(images, id_column='image_id'):
        colors = []
        for id_element in images.index:
            color = constants.COLORS_20[images[id_column][id_element]]
            colors.append(color)
        return colors

    @staticmethod
    def get_legend_elements(elements: GeoDataFrame, legend_column="image_id"):
        legend_elements = []
        for element in elements.index:
            legend_element = mpatches.Circle((0.5, 0.5),
                                             facecolor=constants.COLORS_20[elements[legend_column][element]],
                                             label=elements[legend_column][element])
            legend_elements.append(legend_element)
        return legend_elements

    def set_strategy(self, strategy: Strategy):
        self.strategy = strategy
        # create strategy folder
        folder_strategy = self.working_dir + '/' + strategy.name
        if not os.path.exists(folder_strategy):
            os.makedirs(folder_strategy)
        self.strategy.path = folder_strategy

    def run_experiment(self):
        self.strategy.prepare_strategy(self.aoi, self.images)
        for i in range(self.strategy.number_of_runs):
            self.selected_images_results.append(self.strategy.run_strategy())
        # Process results
        self.process_results()
        # Save results
        self.save_results()

    def process_results(self):
        for key, selected_result in enumerate(self.selected_images_results):
            images_id = ""
            images_id_sorted = ""
            list_to_sort = []
            for image in selected_result.index:
                list_to_sort.append(selected_result['image_id'][image])
                images_id += str(selected_result['image_id'][image]) + '-'
            images_id = images_id[:-1]
            list_to_sort = np.sort(list_to_sort)
            for ids in list_to_sort:
                images_id_sorted += str(ids) + '-'
            images_id_sorted = images_id_sorted[:-1]
            result = ProjectDataClasses.OptimizationResult(experiment_id=key, images_id=images_id,
                                                           images_id_sorted=images_id_sorted,
                                                           number_of_images=len(selected_result))
            self.processed_results.append(result)

    def save_results(self):
        self.save_results_csv()
        self.save_results_coverages()

    def save_results_csv(self):
        file_result_path = self.strategy.path + '/' + EXPERIMENT_RESULTS_FILE
        header = [field.name for field in fields(ProjectDataClasses.OptimizationResult)]
        data = []
        for result in self.processed_results:
            row = list(asdict(result).values())
            data.append(row)

        with open(file_result_path, 'w', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            # write the header
            writer.writerow(header)
            # write the data
            writer.writerows(data)

    def save_results_coverages(self):
        for key, result in enumerate(self.selected_images_results):
            self.config_plot_images_and_aoi(result)
            self.save_coverage_image(self.strategy.path, EXPERIMENT_RESULTS_COVERAGE + str(key) + '.png')
        plt.show()
