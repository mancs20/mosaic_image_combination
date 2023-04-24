from geopandas import GeoDataFrame


class Utilities():
    @staticmethod
    def calculate_area_of_images_in_km2_with_projection(images: GeoDataFrame, projection: dict = {'proj': 'cea'}):
        temp_images = images.to_crs(projection)
        images_area_series = temp_images.area / 10 ** 6
        return images_area_series
