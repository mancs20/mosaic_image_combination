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
        self.data_products = None
        self.api_initialization()

    def get_data_from_marketplace(self):
        # noinspection PyAttributeOutsideInit
        self.result_images = self.search_results(self.collections[0])
        i = 1
        while self.search_parameters.limit > len(self.result_images) and i < len(self.collections):
            images = self.search_results(self.collections[i])
            self.result_images.append(images)
            i += 1
        covered_aoi = True
        if self.search_parameters.limit < 500 and not self.is_aoi_covered_by_searched_images(self.result_images):
            original_limit = self.search_parameters.limit
            self.search_parameters.limit = 500
            [self.result_images, covered_aoi] = self.get_data_from_marketplace()
            if self.is_aoi_covered_by_searched_images(self.result_images):
                self.search_parameters.limit = original_limit
                # random select images to reach the limit and cover the aoi
                self.result_images = self.select_required_images_from_total_to_cover(self.result_images)
            else:
                covered_aoi = False
        return [self.result_images, covered_aoi]

    def api_initialization(self):
        authenticate()
        self.catalog = up42.initialize_catalog()
        self.data_products = self.get_data_products()
        self.associate_data_products_by_collection()

    def get_data_products(self):
        all_data_products = self.catalog.get_data_products()
        #iterate over a dict and get the ones that in dict data_products contains the field Display
        data_products = {}
        for product_name in all_data_products:
            if "Display" in all_data_products[product_name]["data_products"]:
               data_products[all_data_products[product_name]["collection"]] = all_data_products[product_name]
        return data_products

    def associate_data_products_by_collection(self, predefined_collections=True):
        if predefined_collections:
            self.collections.append(self.search_parameters.collections)
        else:
            collections = {}
            for data_product in self.data_products:
                if self.data_products[data_product]['host'] in collections:
                    collections[self.data_products[data_product]['host']].append(
                        self.data_products[data_product]['collection'])
                else:
                    collections[self.data_products[data_product]['host']] = [self.data_products[data_product]['collection']]
            for collection in collections:
                self.collections.append(collections[collection])


    def search_results(self, collection):
        # Search in the catalog with your search parameters
        # collections could be E.g. Pleiades Neo (`pneo`), Pleiades (`phr`), Spot (`spot`)
        search_parameters_up42 = self.catalog.construct_parameters(geometry=self.search_parameters.aoi,
                                                                   start_date=self.search_parameters.start_date,
                                                                   end_date=self.search_parameters.end_date,
                                                                   collections=collection,
                                                                   max_cloudcover=self.search_parameters.max_cloudcover,
                                                                   limit=self.search_parameters.limit)
        return self.catalog.search(search_parameters=search_parameters_up42)

    def update_images_cost(self, images):
        estimated_costs = []
        for index, row in images.iterrows():
            image = row
            data_product_id = self.data_products[image['collection']]['data_products']['Display']
            order_parameters = self.catalog.construct_order_parameters(data_product_id=data_product_id,
                                                                 image_id=image['id'],
                                                                 aoi=self.search_parameters.aoi)
            try:
                estimated_cost = self.catalog.estimate_order(order_parameters=order_parameters)
                estimated_costs.append(estimated_cost)
            except:
                # remove images that cannot be ordered
                images = images.drop(index)
        images['cost'] = estimated_costs
        return images

    def get_quicklooks_from_marketplace(self, images, directory):
        if self.result_images is None:
            self.get_data_from_marketplace()
        # TODO for each tyope of sensor donwload the quicklook
        sensor = {}
        # get all types of sensors in geodataframe images
        for index, row in images.iterrows():
            image = row
            if image['collection'] in sensor:
                sensor[image['collection']].append(image['id'])
            else:
                sensor[image['collection']] = [image['id']]
        # download quicklooks for each type of sensor
        for sensor_type in sensor:
            self.catalog.download_quicklooks(sensor[sensor_type], sensor_type, directory)
        # image_ids = list(images.id)
        # self.catalog.download_quicklooks(image_ids, sensor, directory)

    # def convert_search_parameters_without_aoi_to_json(self):
    #     temp_json = self.search_parameters.to_json()
    #     images_collections = self.search_parameters.collections
    #     string_images_collections = ", \"collections\": \""
    #     for image_collection in images_collections:
    #         string_images_collections += (image_collection + '-')
    #     params_json = temp_json[:-1] + string_images_collections[:-1] + '\"}'
    #     return params_json

    def prepare_data_to_save(self, images):
        images = self.remove_lists_fields(images)
        images = Marketplace.add_id_fields(images)
        return images

    @staticmethod
    def remove_lists_fields(images):
        return images.drop(columns="up42:usageType")
