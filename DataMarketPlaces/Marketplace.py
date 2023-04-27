import random
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from geopandas import GeoDataFrame

import ProjectDataClasses
import constants


class Marketplace(ABC):

    def __init__(self, aoi: GeoDataFrame, search_parameters: ProjectDataClasses.SearchParameters):
        self.aoi = aoi
        self.search_parameters = search_parameters
        self.result_images = None
        self.collections = []

    @abstractmethod
    def api_initialization(self):
        pass

    @abstractmethod
    def get_data_from_marketplace(self) -> [GeoDataFrame,bool]:
        pass

    @abstractmethod
    def search_results(self, collection: str) -> GeoDataFrame:
        pass

    def is_aoi_covered_by_searched_images(self, images):
        all_images_union = images.unary_union  # convert all images (GeoSeries) in a single polygon
        # check if GeoDataFrame is inside a Polygon
        if self.aoi.within(all_images_union)[0]:
            return True
        else:
            print("The images are not covering the whole aoi for " + self.aoi.loc[0]['name'] + " try another search")
            return False
        pass

    def select_required_images_from_total_to_cover(self, all_images, remove_images_covering_less_than25km2=False):
        if remove_images_covering_less_than25km2:
            all_images = self.remove_images_covering_less_than25km2(all_images)
        if self.search_parameters.limit != 500 and len(all_images.index) > self.search_parameters.limit:
            number_of_tries = 100
            cover = False
            while number_of_tries > 0 and cover is False:
                selected_images = self.random_select_images_from_total(all_images, self.search_parameters.limit)
                cover = self.is_aoi_covered_by_searched_images(selected_images)
                number_of_tries -= 1
            return selected_images
        else:
            return all_images

    def remove_images_covering_less_than25km2(self, all_images):
        # return all images which intersect with aoi and cover more than 25km2
        original_crs = all_images.crs
        all_images = all_images.to_crs(constants.PLANAR_CRS)
        self.aoi = self.aoi.to_crs(constants.PLANAR_CRS)

        all_images_intersection_area = all_images.intersection(self.aoi.unary_union).area
        all_images = all_images[all_images_intersection_area > 25000000]

        all_images = all_images.to_crs(original_crs)
        self.aoi = self.aoi.to_crs(original_crs)
        return all_images

    def random_select_images_from_total(self, all_images, number_images):
        # TODO delete this is for having smaller images, we are considering only images les than 1.0m2 resolution
        if number_images < len(all_images[all_images['resolution'] < 1.0]):
            all_images = all_images[all_images['resolution'] < 1.0]

        random_arr = all_images['image_id'].tolist()
        selected_images = all_images[all_images.geom_type != "Polygon"]
        for i in range(number_images):
            id_arr = random.randint(0, len(random_arr) - 1)
            id_image = random_arr[id_arr]
            del random_arr[id_arr]
            selected_image = all_images[all_images['image_id'] == id_image]
            selected_images = selected_images.append(selected_image)
        selected_images.crs = all_images.crs
        selected_images = selected_images.to_crs(all_images.crs)
        return selected_images

    @abstractmethod
    def get_quicklooks_from_marketplace(self, images, directory):
        pass

    @abstractmethod
    def map_quicklooks(
            self,
            scenes: GeoDataFrame,
            aoi: [GeoDataFrame] = None,
            show_images: bool = True,
            show_features: bool = False,
            filepaths: [list] = None,
            name_column: str = "id",
            save_html: Optional[Path] = None,
    ) -> "folium.Map":
        pass

    @abstractmethod
    def update_images_cost(self, images) -> GeoDataFrame:
        pass

    @abstractmethod
    def update_images_incidence_angle(self, images) -> GeoDataFrame:
        pass

    def convert_search_parameters_without_aoi_to_json(self):
        temp_json = self.search_parameters.to_json()
        images_collections = self.search_parameters.collections
        string_images_collections = ", \"collections\": \""
        for image_collection in images_collections:
            string_images_collections += (image_collection + '-')
        params_json = temp_json[:-1] + string_images_collections[:-1] + '\"}'
        return params_json

    @abstractmethod
    def prepare_data_to_save(self, images) -> GeoDataFrame:
        pass

    @staticmethod
    def add_id_fields(images):
        images_id = list(range(len(images.index)))
        images['image_id'] = images_id
        return images
