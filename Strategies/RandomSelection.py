from Strategies.Strategy import Strategy
import random


class RandomSelection(Strategy):
    path = ""
    name = "Random_Selection"
    number_of_runs = 100

    def run_strategy(self):
        results = self.initialize_result()
        array_ids = list(range(len(self.images)))
        while self.aoi.area[0] > 0:
            array_ids_id = random.randint(0, len(array_ids) - 1)
            next_image_id = array_ids[array_ids_id]
            if self.image_intersects_aoi(next_image_id):
                results = self.update_results_and_aoi(next_image_id, results)
            else:
                # noinspection PyAttributeOutsideInit
                self.images = self.images.drop(next_image_id)
            del array_ids[array_ids_id]
        return self.prepare_results_to_return(results)

    def image_intersects_aoi(self, image_id):
        return self.aoi.intersects(self.images.loc[image_id].geometry).values[0]
