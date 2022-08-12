from Strategies.Strategy import Strategy


class GreedyCoverLargerArea(Strategy):
    path = ""
    name = "Greedy_Cover_larger_area"
    number_of_runs = 1

    def run_strategy(self):
        results = self.initialize_result()
        # Repeat until the aoi is covered
        while self.aoi.area[0] > 0:
            # Get the image with the maximum intersecting area in the aoi.
            image_id_max_intersection = self.get_image_id_max_intersection_area()
            # Add image to results and remove it from images and update the area of interest (aoi)
            # subtracting the new image, the result is a new polygon
            results = self.update_results_and_aoi(image_id_max_intersection, results)
        # Return selected images
        return self.prepare_results_to_return(results)

    def get_image_id_max_intersection_area(self):
        intersecting_images_area = self.images.intersection(self.aoi.unary_union).area
        max_area = 0
        max_id = 0
        remove_images = []
        for idx in range(len(intersecting_images_area)):
            area = intersecting_images_area.values[idx]
            if area > max_area:
                max_id = idx
                max_area = area
            if area == 0:
                remove_images.append(self.images.index[idx])

        for id_image in remove_images:
            # noinspection PyAttributeOutsideInit
            self.images = self.images.drop(id_image)

        return intersecting_images_area.index[max_id]
