import copy

from shapely.geometry import LineString
from shapely.ops import unary_union, polygonize

from Strategies.Strategy import Strategy
from abc import abstractmethod

from Strategies.StrategyDiscrete.ImageSet import ImageSet
from Strategies.StrategyDiscrete.Region import Region


class StrategyDiscrete(Strategy):
    def __init__(self):
        super().__init__()
        self.contained_images = None
        self.sets_images = []
        self.universe = 0

    @abstractmethod
    def run_strategy(self):
        pass

    def discretize(self, method="getAllPolygonsWithShapely"):
        self.remove_image_area_outside_aoi()
        self.initialize_set_images()
        if method == "getAllPolygonsWithShapely":
            self.get_intersections_with_shapely()

    def initialize_set_images(self):
        # iterate over geoDataFrame self.contained_images
        for index, row in self.contained_images.iterrows():
            image_set = ImageSet(image_id=row['image_id'], weight=row['cost'], list_of_regions=[])
            self.sets_images.append(image_set)

    def get_intersections_with_shapely(self):
        polygons = self.contained_images.geometry
        rings = [LineString(list(pol.exterior.coords)) for pol in polygons]
        union = unary_union(rings)
        resulting_polygons = [geom for geom in polygonize(union)]
        self.universe = len(resulting_polygons)
        self.associate_resulting_polygons_to_images(resulting_polygons)

    def associate_resulting_polygons_to_images(self, resulting_polygons):
        for i in range(len(resulting_polygons)):
            polygon_centroid = resulting_polygons[i].centroid
            region = Region()
            region.id = i + 1
            region.area = resulting_polygons[i].area
            images_index = []
            for index, row in self.contained_images.iterrows():
                if row['geometry'].contains(polygon_centroid):
                    region.list_of_belonging_image_set.append(row['image_id'])
                    images_index.append(index)
            for belonging_image in region.list_of_belonging_image_set:
                region_copy = copy.deepcopy(region)  # every region has to be a different object because the penalized
                # attribute can be different for each image
                self.sets_images[belonging_image].list_of_regions.append(region_copy)

    @staticmethod
    def plot_polygons(polygons):
        from matplotlib import pyplot as plt

        fig, ax = plt.subplots()
        # for linestring in linestrings:
        #     # extract the x and y coordinates of the line segments
        #     x, y = linestring.xy
        #
        #     # plot the line segments
        #     ax.plot(x, y, color='red', linewidth=2, solid_capstyle='round')

        for polygon in polygons:
            x, y = polygon.exterior.xy
            ax.fill(x, y, alpha=0.5, edgecolor="black")
            centroid = polygon.centroid
            ax.scatter(centroid.x, centroid.y, color='red')
        plt.show()

    def remove_image_area_outside_aoi(self):
        intersection_images_aoi = self.images.intersection(self.aoi.unary_union)
        self.contained_images = self.images.set_geometry(intersection_images_aoi)
