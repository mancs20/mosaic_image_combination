# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from ProjectDataClasses import SearchParameters
from Experiment import Experiment
from DataMarketPlaces.MarketplaceUp42 import MarketplaceUp42
from Strategies.GreedyCoverLargerArea import GreedyCoverLargerArea


def get_aoi_file():
    file = "aois/dakar.geojson"
    return file


def get_search_parameters():
    search_parameters = SearchParameters()  # Default values
    return search_parameters


def main():
    aoi_file = get_aoi_file()
    search_parameters = get_search_parameters()
    experiment = Experiment(search_parameters=search_parameters, aoi_file=aoi_file)
    experiment.set_marketplace(MarketplaceUp42(experiment.aoi, experiment.search_parameters))
    experiment.set_strategy(GreedyCoverLargerArea())

    if not (experiment.prepare_experiment()):
        return
    experiment.run_experiment()


if __name__ == '__main__':
    main()
    print("Finished experiments")
