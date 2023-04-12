from shapely.geometry import LineString
from shapely.ops import unary_union, polygonize

from Strategies.Strategy import Strategy
from abc import abstractmethod

from Strategies.StrategyDiscrete.ImageSet import ImageSet


class StrategyDiscrete(Strategy):
    def __init__(self):
        super().__init__()
        self.contained_images = None
        self.sets_images = []
        self.universe = []

    @abstractmethod
    def run_strategy(self):
        pass

    def discretize(self, method="getAllPolygonsWithShapely"):
        self.remove_image_area_outside_aoi()
        self.initialize_set_images()
        if method == "getAllPolygonsWithShapely":
            self.get_intersections_with_shapely()

    def initialize_set_images(self):
        for i in range(len(self.contained_images)):
            image_set = ImageSet(image_id=self.contained_images.loc[i, 'image_id'],
                                 weight=self.contained_images.loc[i, 'area'], list_of_regions=[])
            self.sets_images.append(image_set)

    def get_intersections_with_shapely(self):
        polygons = self.contained_images.geometry
        rings = [LineString(list(pol.exterior.coords)) for pol in polygons]
        union = unary_union(rings)
        resulting_polygons = [geom for geom in polygonize(union)]
        self.universe = len(resulting_polygons)
        self.associate_resulting_polygons_to_images(resulting_polygons)

    def associate_resulting_polygons_to_images(self, resulting_polygons):
        for i in range(len(self.sets_images)):
            for j in range(len(resulting_polygons)):
                polygon_centroid = resulting_polygons[j].centroid
                if self.contained_images.loc[i, 'geometry'].contains(polygon_centroid):
                    self.sets_images[i].list_of_regions.append(j + 1)

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