import collections
import csv
import json
import os
import re
from abc import ABC
from dataclasses import fields, asdict
from typing import Union

import geopandas
import contextily as cx
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import random
import up42
from geopandas import GeoDataFrame

import ProjectDataClasses
import constants
from DataMarketPlaces import Marketplace
from Strategies import Strategy

DATA_FILE_NAME_CSV = 'images_data.csv'
DATA_FILE_NAME = 'images_data.geojson'
COVERAGE_IMAGE_NAME = 'coverage.png'
EXPERIMENT_RESULTS_FILE = 'experiment_results.csv'
EXPERIMENT_RESULTS_GEOJSON = 'experiment_results_'
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

    def print_aoi_area(self):
        # show aoi area
        self.aoi.crs = 4326
        temp_aoi = self.aoi.to_crs(constants.PLANAR_CRS)
        print('Area of aoi ' + self.working_dir + ' is: ' + str(temp_aoi.area[0] / 1000000))

    def prepare_experiment(self):
        # Create or get folder for experiment results
        failed_experiment = False
        if not self.check_if_local_data():
            raw_images = self.marketplace.get_data_from_marketplace()
            if self.is_aoi_covered_by_searched_images(raw_images):
                self.images = self.select_required_images_from_total_to_cover(raw_images, number_images=30)
                self.images.crs = raw_images.crs
                self.images.to_crs(self.images.crs)
                if not self.is_aoi_covered_by_searched_images(self.images):
                    failed_experiment = True
                else:
                    # TODO uncomment below to get images marketplace cost
                    # self.images = self.marketplace.update_images_cost()
                    self.save_data()
            else:
                self.images = raw_images
                failed_experiment = True
            if failed_experiment:
                # to plot the images and see why the cover is failling
                self.images = self.marketplace.prepare_data_to_save(self.images)
        else:
            self.images = geopandas.read_file(self.working_dir + '/' + DATA_FILE_NAME)
        self.config_plot_images_and_aoi(self.images, self.aoi)
        plt.show()
        if failed_experiment is True:
            return False
        # set aoi with the same crs (projection system) as the images
        self.aoi.crs = self.images.crs
        self.aoi.to_crs(self.aoi.crs)
        return True

    def select_required_images_from_total_to_cover(self, all_images, number_images=30):
        if len(all_images.index) > number_images:
            number_of_tries = max(100, 2 ** len(all_images.index))
            cover = False
            while number_of_tries > 0 and cover is False:
                selected_images = self.random_select_images_from_total(all_images, number_images)
                cover = self.is_aoi_covered_by_searched_images(selected_images)
                number_of_tries -= 1

            return selected_images
        else:
            return all_images

    def random_select_images_from_total(self, all_images, number_images=30):
        random_arr = list(range(len(all_images.index)))
        selected_images = all_images[all_images.geom_type != "Polygon"]
        for i in range(number_images):
            id_arr = random.randint(0, len(random_arr) - 1)
            id_image = random_arr[id_arr]
            del random_arr[id_arr]
            selected_image = all_images.loc[id_image]
            selected_images = selected_images.append(selected_image)
        return selected_images

    def check_create_working_dir(self, aoi_file):
        current_dir = os.path.dirname(__file__)
        dir_name = re.search('/(.*).geojson', aoi_file).group(1)
        self.working_dir = os.path.join(current_dir, 'results', dir_name)
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

    def check_if_local_data(self):
        return os.path.exists(self.working_dir + '/' + DATA_FILE_NAME)

    def is_aoi_covered_by_searched_images(self, images):
        all_images_union = images.unary_union  # convert all images (GeoSeries) in a single polygon
        # check if GeoDataFrame is inside a Polygon
        if self.aoi.within(all_images_union)[0]:
            return True
        else:
            print("The images are not covering the whole aoi for " + self.working_dir + " try another search")
            return False
        pass

    def save_data(self):
        # donwload quicklooks
        quicklooks = self.marketplace.get_quicklooks_from_marketplace(self.images, self.working_dir + "/quicklooks")
        # add field image_id and remove fields with lists
        self.images = self.marketplace.prepare_data_to_save(self.images)
        # save data to csv, human readable
        self.images.to_csv(self.working_dir + '/' + DATA_FILE_NAME_CSV, index_label='image_id')
        # save to geojson, remove fields with lists, for shp is the same
        self.images.to_file(self.working_dir + '/' + DATA_FILE_NAME, driver='GeoJSON')
        self.save_search_parameters()
        self.config_plot_images_and_aoi(self.images, self.aoi)
        self.save_coverage_image(self.working_dir, COVERAGE_IMAGE_NAME)

    def save_search_parameters(self):
        params_json = self.marketplace.convert_search_parameters_without_aoi_to_json()
        file_name = self.working_dir + '/search_parameters.json'
        with open(file_name, 'w') as outfile:
            outfile.write(json.dumps(params_json))

    @staticmethod
    def save_coverage_image(path, image_name):
        plt.savefig(path + '/' + image_name)

    @staticmethod
    def config_plot_images_and_aoi(images, aoi, legend_column="image_id", basemap=True):
        legend_elements = Experiment.get_legend_elements(images, legend_column)
        fig_size = (10, 10)
        if len(legend_elements) > 0:
            colors = Experiment.get_plot_colors(images)
            ax = images.plot(categorical=True,
                             figsize=fig_size,
                             legend=True,
                             alpha=0.7,
                             color=colors)
            ax.legend(handles=legend_elements, loc="upper left", bbox_to_anchor=(1, 1))
        else:
            ax = images.plot(legend_column,
                             categorical=True,
                             figsize=fig_size,
                             legend=True,
                             alpha=0.7,
                             cmap="Set3",
                             legend_kwds=dict(loc="upper left", bbox_to_anchor=(1, 1)))
        aoi.plot(color="r", ax=ax, fc="None", edgecolor="r", lw=1)
        if basemap:
            cx.add_basemap(ax, crs=images.crs)

        return ax

    @staticmethod
    def get_plot_colors(images, id_column='image_id'):
        colors = []
        for id_element in images.index:
            color = constants.COLORS_30[images[id_column][id_element]]
            colors.append(color)
        return colors

    @staticmethod
    def get_legend_elements(elements: GeoDataFrame, legend_column="image_id"):
        legend_elements = []
        legend_colors = constants.COLORS_30
        if len(elements.index) <= len(legend_colors):
            for element in elements.index:
                legend_element = mpatches.Circle((0.5, 0.5),
                                                 facecolor=legend_colors[elements[legend_column][element]],
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
        for i in range(self.strategy.number_of_runs):
            self.strategy.prepare_strategy(self.aoi, self.images)
            self.selected_images_results.append(self.strategy.run_strategy())
        # Process results
        self.process_results()
        # Save results
        self.save_results()

    def process_results(self):
        check_duplicates_exact = []
        check_duplicates_after_sort = []
        for key, selected_result in enumerate(self.selected_images_results):
            images_id = ""
            images_id_sorted = ""
            list_to_sort = []
            for image in selected_result.index:
                list_to_sort.append(selected_result['image_id'][image])
                images_id += str(selected_result['image_id'][image]) + '-'
            images_id = images_id[:-1]
            check_duplicates_exact.append(images_id)
            list_to_sort = np.sort(list_to_sort)
            for ids in list_to_sort:
                images_id_sorted += str(ids) + '-'
            images_id_sorted = images_id_sorted[:-1]
            check_duplicates_after_sort.append(images_id_sorted)
            # geometric metrics
            area_of_images = self.get_area_of_images(selected_result)
            area_of_images_over_aoi = self.get_area_of_images_over_aoi(area_of_images, self.aoi)
            result = ProjectDataClasses.OptimizationResult(experiment_id=key, images_id=images_id,
                                                           images_id_sorted=images_id_sorted,
                                                           number_of_images=len(selected_result),
                                                           area_of_images_km2=(area_of_images / 1000000.0),
                                                           area_of_images_over_aoi=area_of_images_over_aoi)
            self.processed_results.append(result)
        # detect if there are duplicate solutions
        print('Duplicates exact for ' + self.working_dir + ' with strategy ' + self.strategy.name + ' :')
        print([item for item, count in collections.Counter(check_duplicates_exact).items() if count > 1])
        print('Duplicates after sort for ' + self.working_dir + ' with strategy ' + self.strategy.name + ' :')
        print([item for item, count in collections.Counter(check_duplicates_after_sort).items() if count > 1])

    @staticmethod
    def get_area_of_images(selected_result: GeoDataFrame):
        selected_result = selected_result.to_crs(constants.PLANAR_CRS)
        areas = selected_result.area
        total_area = 0.0
        for index, area in areas.items():
            total_area += area
        return total_area

    @staticmethod
    def get_area_of_images_over_aoi(total_area: float, aoi: GeoDataFrame):
        aoi = aoi.to_crs(constants.PLANAR_CRS)
        return total_area / aoi.area[0]

    def save_results(self):
        self.save_results_csv()
        self.save_results_coverages()
        self.save_results_geojson()

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
            ax = self.config_plot_images_and_aoi(result, self.aoi)
            self.save_coverage_image(self.strategy.path, EXPERIMENT_RESULTS_COVERAGE + str(key) + '.png')
            plt.close(ax.figure)

    def save_results_geojson(self):
        file_result_path_root = self.strategy.path + '/' + EXPERIMENT_RESULTS_GEOJSON
        for key, result in enumerate(self.selected_images_results):
            file_result_path = file_result_path_root + str(key) + '.geojson'
            result.to_file(file_result_path, driver='GeoJSON')
