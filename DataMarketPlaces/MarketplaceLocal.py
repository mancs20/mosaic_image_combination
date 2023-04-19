import os.path

import geopandas

import constants
from DataMarketPlaces.Marketplace import Marketplace
from Experiment import Experiment


class MarketplaceLocal(Marketplace):
    def __init__(self, aoi, search_parameters):
        super(MarketplaceLocal, self).__init__(aoi, search_parameters)
    def api_initialization(self):
        pass

    def get_data_from_marketplace(self):
        self.result_images = self.search_results()
        if self.result_images.empty:
            covered_aoi = False
        else:
            self.result_images = self.select_required_images_from_total_to_cover(self.result_images)
            covered_aoi = self.is_aoi_covered_by_searched_images(self.result_images)
        return [self.result_images, covered_aoi]

    def search_results(self):
        working_dir = Experiment.check_create_working_dir(aoi_file=self.aoi.loc[0]['name'],number_images_per_aoi=self.search_parameters.limit)
        working_dir = working_dir[:working_dir.rfind('/')]
        working_dir = os.path.join(working_dir, str(500))
        if not os.path.exists(working_dir):
            print("No local data for " + self.aoi.loc[0]['name'] + " yet")
            images = geopandas.GeoDataFrame(columns=['id', 'distance', 'feature'], geometry='feature', crs='EPSG:4326')
        else:
            images = Experiment.get_local_images_data_from_file(working_dir)
            images = self.filter_images_parameters(images)
        return images

    def filter_images_parameters(self, images):
        images = images[self.search_parameters.start_date <= images['acquisitionDate']]
        images = images[self.search_parameters.end_date >= images['acquisitionDate']]
        images = images[images['cloudCoverage'] <= self.search_parameters.max_cloudcover]
        return images

    def get_quicklooks_from_marketplace(self, images, directory):
        # return list of quicklook image file paths
        # TODO check what are the names of the quicklook images and return them
        list_of_quicklooks = []
        for index, row in images.iterrows():
            quicklook_name = "quicklook_" + str(index) + ".jpg"
            list_of_quicklooks.append(quicklook_name)
        return list_of_quicklooks

    def update_images_cost(self, images):
        return images

    def prepare_data_to_save(self, images):
        images['local_image_id'] = images['image_id']
        images = Marketplace.add_id_fields(images)
        return images