from abc import ABC, abstractmethod
from geopandas import GeoDataFrame
from pandas import Series


def update_results_and_aoi(image_id: int, images: GeoDataFrame, results: GeoDataFrame, aoi: GeoDataFrame):
    selected_image = images.loc[image_id]
    results = results.append(selected_image)
    # Update the area of interest, aoi subtracting the new image, the result is a new polygon
    aoi = aoi.difference(selected_image.geometry)
    images = images.drop(image_id)
    return [results, aoi, images]


class Strategy(ABC):
    @abstractmethod
    def run_strategy(self, aoi_file, search_parameters):
        pass

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

