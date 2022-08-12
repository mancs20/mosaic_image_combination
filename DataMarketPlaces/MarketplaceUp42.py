import up42
from up42 import Catalog

from DataMarketPlaces.Marketplace import Marketplace


def authenticate():
    up42.authenticate(cfg_file='config.json')


class MarketplaceUp42(Marketplace):
    # up42 catalog
    catalog: Catalog

    def __init__(self, aoi, search_parameters):
        super(MarketplaceUp42, self).__init__(aoi, search_parameters)

    def get_data_from_marketplace(self):
        self.api_initialization()
        # noinspection PyAttributeOutsideInit
        self.result_images = self.search_results()
        return self.result_images

    def api_initialization(self):
        authenticate()
        self.catalog = up42.initialize_catalog()

    def search_results(self):
        # Search in the catalog with your search parameters
        # collections could be E.g. Pleiades Neo (`pneo`), Pleiades (`phr`), Spot (`spot`)
        search_parameters_up42 = self.catalog.construct_parameters(geometry=self.search_parameters.aoi,
                                                                   start_date=self.search_parameters.start_date,
                                                                   end_date=self.search_parameters.end_date,
                                                                   collections=self.search_parameters.collections,
                                                                   max_cloudcover=self.search_parameters.max_cloudcover,
                                                                   limit=self.search_parameters.limit)
        return self.catalog.search(search_parameters=search_parameters_up42)

    def update_images_cost(self):
        estimated_costs = []
        for i in range(len(self.result_images)):
            estimated_cost = self.catalog.estimate_order(geometry=self.search_parameters.aoi,
                                                         scene=self.result_images.loc[i])
            estimated_costs.append(estimated_cost)
        self.result_images['Cost'] = estimated_costs
        return self.result_images

    def convert_search_parameters_without_aoi_to_json(self):
        temp_json = self.search_parameters.to_json()
        images_collections = self.search_parameters.collections
        string_images_collections = ", \"collections\": \""
        for image_collection in images_collections:
            string_images_collections += (image_collection + '-')
        params_json = temp_json[:-1] + string_images_collections[:-1] + '\"}'
        return params_json

    def prepare_data_to_save(self, images):
        images = self.remove_lists_fields(images)
        self.add_id_fields(images)
        return images

    @staticmethod
    def remove_lists_fields(images):
        return images.drop(columns="up42:usageType")

    @staticmethod
    def add_id_fields(images):
        images_id = list(images.index)
        images['image_id'] = images_id
