from abc import ABC, abstractmethod
from geopandas import GeoDataFrame
from pandas import Series

PLANAR_CRS = 3857


class Strategy(ABC):
    # noinspection PyTypeChecker
    def __init__(self):
        self.aoi: GeoDataFrame = None
        self.images: GeoDataFrame = None
        self.original_projection: int = None

    @abstractmethod
    def run_strategy(self, aoi, images):
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
        self.images = images
        self.change_projection_to_planar_crs()

    def change_projection_to_planar_crs(self, crs=PLANAR_CRS):
        self.original_projection = self.images.crs
        self.aoi = self.aoi.to_crs(crs)
        self.images = self.images.to_crs(crs)

    def prepare_results_to_return(self, results):
        results.crs = self.images.crs
        results = results.to_crs(self.original_projection)
        return results

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
