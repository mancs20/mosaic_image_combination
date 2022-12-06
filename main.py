# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from DataMarketPlaces.MarketplaceUp42 import MarketplaceUp42
from Experiment import Experiment
from ProjectDataClasses import SearchParameters
from Strategies.GreedyRatioCoveredAoiImageArea import GreedyRatioCoveredAoiImageArea
from Strategies.RandomSelection import RandomSelection


def get_aoi_file():
    # file = "aois/mexico_city.geojson"
    # file = "aois/rio_de_janeiro.geojson"
    # file = "aois/paris.geojson"
    # file = "aois/lagos_nigeria.geojson"
    file = "aois/tokyo_bay.geojson"
    # file = "aois/dakar.geojson"
    return file


def get_aoi_files():
    # Test with only 1 file
    files = [get_aoi_file()]
    # files = ['aois/mexico_city.geojson', 'aois/rio_de_janeiro.geojson',
    #          'aois/paris.geojson', 'aois/lagos_nigeria.geojson', 'aois/tokyo_bay.geojson']
    return files


def get_search_parameters():
    search_parameters = SearchParameters()  # Default values
    return search_parameters


def get_solutions():
    solutions = []
    # solutions for a certain aoi
    # solutions.append("17-12-7-23-5-11-1-4")  # Greedy
    # solutions.append("13-11-19-17-29-12-1")  # Best random
    # solutions.append("12-23-29-4-5-25-13-28-1-0-24-22-6-7-11-10")  # Worst random
    return solutions


def main():
    aoi_files = get_aoi_files()
    search_parameters = get_search_parameters()
    for aoi_file in aoi_files:
        experiment = Experiment(search_parameters=search_parameters, aoi_file=aoi_file)
        experiment.set_marketplace(MarketplaceUp42(experiment.aoi, experiment.search_parameters))

        # To know the area of the aoi, uncomment below
        # experiment.print_aoi_area()

        # strategies = [GreedyRatioCoveredAoiImageArea(), GreedyCoverLargerArea(), RandomSelection()]
        strategies = [GreedyRatioCoveredAoiImageArea(), RandomSelection()]
        if experiment.prepare_experiment():
            # to plot certain solutions and all the images of one aoi uncomment below
            if len(get_solutions()) != 0:
                experiment.plot_all_images_and_solutions(get_solutions())
            else:
                for strategy in strategies:
                    experiment.set_strategy(strategy)
                    experiment.run_experiment()


if __name__ == '__main__':
    main()
    print("Finished experiments")
