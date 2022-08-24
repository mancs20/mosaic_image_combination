# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from DataMarketPlaces.MarketplaceUp42 import MarketplaceUp42
from Experiment import Experiment
from ProjectDataClasses import SearchParameters
from Strategies.GreedyRatioCoveredAoiImageArea import GreedyRatioCoveredAoiImageArea
from Strategies.RandomSelection import RandomSelection


def get_aoi_file():
    file = "aois/dakar.geojson"
    file = "aois/paris.geojson"  # is not good
    return file


def get_aoi_files():
    # Test with only 1 file
    files = [get_aoi_file()]
    # files = ['aois/lagos_nigeria.geojson', 'aois/mexico_city.geojson',
    #          'aois/rio_de_janeiro.geojson', 'aois/tokio_yokohama.geojson', 'aois/dakar.geojson']
    # files = ['aois/luxembourg_south.geojson', 'aois/lagos_nigeria.geojson', 'aois/mexico_city.geojson',
    #          'aois/rio_de_janeiro.geojson', 'aois/tokio_yokohama.geojson', 'aois/dakar.geojson']
    files = ['aois/cairo.geojson']
    return files


def get_search_parameters():
    search_parameters = SearchParameters()  # Default values
    return search_parameters


def main():
    aoi_files = get_aoi_files()
    search_parameters = get_search_parameters()
    for aoi_file in aoi_files:
        experiment = Experiment(search_parameters=search_parameters, aoi_file=aoi_file)
        experiment.set_marketplace(MarketplaceUp42(experiment.aoi, experiment.search_parameters))

        experiment.print_aoi_area()

        # strategies = [GreedyRatioCoveredAoiImageArea(), GreedyCoverLargerArea(), RandomSelection()]
        strategies = [GreedyRatioCoveredAoiImageArea(), RandomSelection()]
        if experiment.prepare_experiment():
            for strategy in strategies:
                experiment.set_strategy(strategy)
                experiment.run_experiment()


if __name__ == '__main__':
    main()
    print("Finished experiments")
