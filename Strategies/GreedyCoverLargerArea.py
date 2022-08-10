from Strategies.Strategy import Strategy, update_results_and_aoi
import matplotlib.pyplot as plt


class GreedyCoverLargerArea(Strategy):
    path = ""
    name = "Greedy_Cover_larger_area"
    number_of_runs = 1

    def run_strategy(self, aoi, images):
        old_crs = aoi.crs
        aoi, images = self.change_projection_to_mts(aoi, images)

        results = images[images.geom_type != "Polygon"]

        # Repeat until the aoi is covered
        while aoi.area[0] > 0:
            # Get the image with the maximum intersecting area in the aoi.
            image_id_max_intersection, images = self.get_image_id_max_intersection_area(aoi, images)
            # Add image to results and remove it from images
            # Update the area of interest, aoi subtracting the new image, the result is a new polygon
            results, aoi, images = update_results_and_aoi(image_id_max_intersection, images, results, aoi)

            # TODO delete, this is to see the algorithm
            # figsize = (12, 16)
            # ax = results.plot(alpha=0.7, figsize=figsize)
            # aoi.plot(color="r", alpha=0.7, ax=ax, fc="None", edgecolor="r", lw=1)
            # plt.show()

        # Return selected images
        results.crs = images.crs
        results = results.to_crs(old_crs)
        return results

    @staticmethod
    def get_image_id_max_intersection_area(aoi, images):
        intersecting_images_area = images.intersection(aoi.unary_union).area
        max_area = 0
        max_id = 0
        remove_images = []
        for idx in range(len(intersecting_images_area)):
            area = intersecting_images_area.values[idx]
            if area > max_area:
                max_id = idx
                max_area = area
            if area == 0:
                remove_images.append(images.index[idx])

        for id_image in remove_images:
            images = images.drop(id_image)

        return intersecting_images_area.index[max_id], images
