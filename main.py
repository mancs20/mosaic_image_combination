# This is a sample Python script.
from DataMarketPlaces.MarketplaceLocal import MarketplaceLocal
# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from DataMarketPlaces.MarketplaceUp42 import MarketplaceUp42
from Experiment import Experiment
from ProjectDataClasses import SearchParameters
from Strategies.GreedyRatioCoveredAoiImageArea import GreedyRatioCoveredAoiImageArea
from Strategies.RandomSelection import RandomSelection
from Strategies.StrategyDiscrete.CPClouds import CPClouds
from Strategies.StrategyDiscrete.CPWithouyClouds import CPWithoutClouds


def get_aoi_file():
    # file = "aois/mexico_city.geojson"
    # file = "aois/rio_de_janeiro.geojson"
    file = "aois/paris.geojson"
    # file = "aois/lagos_nigeria.geojson"
    # file = "aois/tokyo_bay.geojson"
    # file = "aois/dakar.geojson"
    return file


def get_aoi_files():
    # Test with only 1 file
    files = [get_aoi_file()]

    # files = ['aois/mexico_city.geojson', 'aois/rio_de_janeiro.geojson',
    #          'aois/paris.geojson', 'aois/lagos_nigeria.geojson', 'aois/tokyo_bay.geojson']

    # files = ['aois/mexico_city.geojson', 'aois/rio_de_janeiro.geojson',
    #          'aois/lagos_nigeria.geojson', 'aois/tokyo_bay.geojson']
    return files


def get_search_parameters():
    search_parameters = SearchParameters()  # Default values
    return search_parameters


def get_solutions():
    solutions = []
    # all images and the aoi
    # solutions.append("0-1-2-3-4-5-6-7-8-9-10-11-12-13-14-15-16-17-18-19-20-21-22-23-24-25-26-27-28-29")
    # solutions for a certain aoi
    # solutions.append("17-12-7-23-5-11-1-4")  # Greedy
    # solutions.append("13-11-19-17-29-12-1")  # Best random
    # solutions.append("12-23-29-4-5-25-13-28-1-0-24-22-6-7-11-10")  # Worst random
    return solutions


def main():
    aoi_files = get_aoi_files()
    search_parameters = get_search_parameters()
    # To print all the aoi in the world map uncomment below
    # aois = Experiment.process_several_aois(aoi_files)
    # Experiment.plot_aois(aois)

    for aoi_file in aoi_files:
        experiment = Experiment(search_parameters=search_parameters, aoi_file=aoi_file)
        # experiment.set_marketplace(MarketplaceUp42(experiment.aoi, experiment.search_parameters))
        experiment.set_marketplace(MarketplaceLocal(experiment.aoi, experiment.search_parameters))

        # To know the area of the aoi, uncomment below
        # experiment.print_aoi_area()

        # strategies = [GreedyRatioCoveredAoiImageArea(), GreedyCoverLargerArea(), RandomSelection()]
        # strategies = [GreedyRatioCoveredAoiImageArea(), RandomSelection()]
        # strategies = [CPWithoutClouds()]
        strategies = [CPClouds()]
        # strategies = []
        if experiment.prepare_experiment():
            # to plot certain solutions and all the images of one aoi uncomment below, it works if len(aoi_file) = 1
            if len(get_solutions()) != 0:
                experiment.plot_all_images_and_solutions(get_solutions())
            else:
                for strategy in strategies:
                    experiment.set_strategy(strategy)
                    experiment.run_experiment()


if __name__ == '__main__':
    main()
    print("Finished experiments")
