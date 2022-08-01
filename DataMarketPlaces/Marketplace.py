from abc import ABC, abstractmethod
from geopandas import GeoDataFrame
import ProjectDataClasses


class Marketplace(ABC):

    def __init__(self, aoi: GeoDataFrame, search_parameters: ProjectDataClasses.SearchParameters):
        self.aoi = aoi
        self.search_parameters = search_parameters
        self.result_images = None

    @abstractmethod
    def api_initialization(self):
        pass

    @abstractmethod
    def get_data_from_marketplace(self):
        pass

    @abstractmethod
    def search_results(self):
        pass

    @abstractmethod
    def is_aoi_covered_by_searched_images(self):
        pass

    @abstractmethod
    def update_images_cost(self):
        pass

    @abstractmethod
    def convert_search_parameters_without_aoi_to_json(self):
        pass

    @abstractmethod
    def prepare_data_to_save(self, images):
        pass
