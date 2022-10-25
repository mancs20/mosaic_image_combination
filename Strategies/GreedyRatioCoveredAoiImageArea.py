from Strategies.Strategy import Strategy


class GreedyRatioCoveredAoiImageArea(Strategy):
    path = ""
    name = "Greedy_Ratio_Covered_Aoi_Image_Area"
    number_of_runs = 1

    def run_strategy(self):
        results = self.initialize_result()
        while self.aoi.area[0] > 0:
            image_id_max_intersection = self.get_image_id_max_ratio_cover_area()
            results = self.update_results_and_aoi(image_id_max_intersection, results)
            # print results to debug the algorithm
            # self.print_temp_results(results)
        return self.prepare_results_to_return(results)

    def get_image_id_max_ratio_cover_area(self):
        intersecting_images_area = self.images.intersection(self.aoi.unary_union).area
        images_areas = self.images.area
        max_area_ratio = 0.0
        max_area = 0.0
        greedy_tuple = (max_area_ratio, max_area)
        max_id = 0
        remove_images = []
        for idx in range(len(intersecting_images_area)):
            intersecting_area = intersecting_images_area.values[idx]
            if intersecting_area == 0:
                remove_images.append(self.images.index[idx])
            else:
                image_area = images_areas.values[idx]
                area_ratio = intersecting_area / image_area
                image_tuple = (area_ratio, image_area)
                if image_tuple[0] > greedy_tuple[0] or (image_tuple[0] == greedy_tuple[0] and
                                                        image_tuple[1] > greedy_tuple[1]):
                    max_id = idx
                    greedy_tuple = image_tuple

        for id_image in remove_images:
            # noinspection PyAttributeOutsideInit
            self.images = self.images.drop(id_image)

        return intersecting_images_area.index[max_id]
