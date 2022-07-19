# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
import up42


# def print_hi(name):
#     # Use a breakpoint in the code line below to debug your script.
#     print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.
#
#
# # Press the green button in the gutter to run the script.


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
def authenticate():
    up42.authenticate(cfg_file="config.json")


def get_aoi_file():
    file = "aois/luxembourg_rectangle.geojson"
    return file


def example_30s():
    authenticate()
    catalog = up42.initialize_catalog()
    # Search in the catalog with your search parameters
    aoi = up42.read_vector_file(get_aoi_file())
    search_parameters = catalog.construct_parameters(geometry=aoi,
                                                     start_date="2019-01-01",
                                                     end_date="2021-12-31",
                                                     collections=["phr"],
                                                     max_cloudcover=20,
                                                     limit=10)
    search_results = catalog.search(search_parameters=search_parameters)

    # Estimate the order price and place the order
    estimated_cost = catalog.estimate_order(geometry=aoi, scene=search_results.loc[0])
    return estimated_cost


if __name__ == '__main__':
    print("Estimated cost: " + str(example_30s()))
