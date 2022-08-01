# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
from typing import List

import geopandas
import up42
from shapely.geometry import Polygon

from ProjectDataClasses import SearchParameters
from Experiment import Experiment


import constants
# from SearchParameters import SearchParameters

# def print_hi(name):
#     # Use a breakpoint in the code line below to debug your script.
#     print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.
#
#
# # Press the green button in the gutter to run the script.


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
from geopandas import GeoDataFrame

from DataMarketPlaces.MarketplaceUp42 import MarketplaceUp42
from Strategies.GreedyCoverLargerArea import GreedyCoverLargerArea


def authenticate():
    up42.authenticate(cfg_file="config.json")


def get_aoi_file():
    file = "aois/dakar.geojson"
    return file


def get_search_parameters():
    search_parameters = SearchParameters()  # Default values
    return search_parameters


def example_30s():
    authenticate()
    catalog = up42.initialize_catalog()
    # Search in the catalog with your search parameters
    aoi = up42.read_vector_file(get_aoi_file())
    search_parameters = catalog.construct_parameters(geometry=aoi,
                                                     start_date="2020-01-01",
                                                     end_date="2022-07-21",
                                                     collections=["phr"],
                                                     max_cloudcover=50,
                                                     limit=20)

    search_results = catalog.search(search_parameters=search_parameters)

    aoi_geo = geopandas.GeoDataFrame.from_features(aoi)  # convert to GeoDataFram, so it can be plotted in coverage
    all_images_union = search_results.unary_union  # convert all images (GeoSeries) in a single polygon
    aoi_geo.within(all_images_union)  # check if GeoDataFrame is inside a Polygon

    # Estimate the order price and place the order
    estimated_cost = catalog.estimate_order(geometry=aoi, scene=search_results.loc[1])
    catalog.plot_coverage(search_results, aoi_geo)
    return estimated_cost


def run_tests(aoi_file, search_parameters, heuristic=constants.RANDOM):
    authenticate()
    catalog = up42.initialize_catalog()
    # Search in the catalog with your search parameters
    aoi = up42.read_vector_file(aoi_file)
    search_parameters.aoi = aoi
    search_parameters_up42 = catalog.construct_parameters(geometry=search_parameters.aoi,
                                                          start_date=search_parameters.start_date,
                                                          end_date=search_parameters.end_date,
                                                          collections=search_parameters.collections,
                                                          max_cloudcover=search_parameters.max_cloudcover,
                                                          limit=search_parameters.limit)
    search_results = catalog.search(search_parameters=search_parameters_up42)
    aoi_geo = geopandas.GeoDataFrame.from_features(aoi)  # convert to GeoDataFram, so it can be plotted in coverage
    # Plot all the images and the aoi
    catalog.plot_coverage(search_results, aoi_geo)

    all_images_union = search_results.unary_union  # convert all images (GeoSeries) in a single polygon
    # check if GeoDataFrame is inside a Polygon
    if len(aoi_geo.within(all_images_union)) == 0:
        print("The images are not covering the whole aoi, try another search")
        return
    else:
        if heuristic == constants.GREEDY_COVER_LARGER_AREA:
            seleted_images = greedy_cover_larger_area(aoi_geo, search_results)
        else:
            seleted_images = random_cover(aoi_geo, search_results)
    catalog.plot_coverage(seleted_images, aoi_geo)  # plot the selected images

    # return optimization criteria, e.g. number of images, total area, etc
    optimization_results = OptimizationResult()
    optimization_results.number_of_images = len(seleted_images)
    # TODO find out how to sum all the images area
    optimization_results.total_area_of_images = 2
    return optimization_results


def intersecting_area(polygon1, polygon2):
    return polygon1.intersection(polygon2)


def get_max_intersection_area(aoi, images):
    intersecting_areas = images.intersection(aoi.unary_union).area
    max_area = 0
    max_id = 0
    for idx in range(len(intersecting_areas)):
        area = intersecting_areas.values[idx]
        if area > max_area:
            max_id = idx
            max_area = area
    return intersecting_areas.index[max_id]


def greedy_cover_larger_area(aoi, images):
    results = images[images.geom_type != "Polygon"]
    # Repeat until the aoi is covered
    while aoi.area > 0:
        # Get the image with the maximum intersecting area in the aoi.
        max_intersecting_area_index = get_max_intersection_area(aoi, images)
        # Add image to results and remove it from images
        selected_image = images.loc[max_intersecting_area_index].geometry
        results = results.append(selected_image)
        # Update the area of interest, aoi subtracting the new image, the result is a new polygon
        aoi = aoi.difference(selected_image)
    # Return selected images
    return results


def random_cover(aoi, images):
    a = 1


def main():
    aoi_file = get_aoi_file()
    search_parameters = get_search_parameters()
    experiment = Experiment(search_parameters=search_parameters, aoi_file=aoi_file)
    experiment.set_marketplace(MarketplaceUp42(experiment.aoi, experiment.search_parameters))
    experiment.set_strategy(GreedyCoverLargerArea())

    if not (experiment.prepare_experiment()):
        return
    experiment.run_experiment(experiment.aoi, experiment.images)


if __name__ == '__main__':
    # example_30s()
    main()
    #run_tests(get_aoi_file(), get_search_parameters(), constants.GREEDY_COVER_LARGER_AREA)
    print("Finished experiments")
