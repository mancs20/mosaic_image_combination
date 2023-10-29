from MO import MO

from ParetoFront import ParetoFront

# todo change name this is MO when minizinc is not used
class MOMIP:
    """Multi-objective solver maintaining a Pareto front.
         See further information in the class `ParetoFront`.
      Args:
        instance (Instance): A constraint model.
        statistics (dict): A dictionary to store the statistics of the solver.
        front_generator: A front generator strategy with a solver supporting `solve()`.
        verbose (Bool): If `True`, the solver prints the Pareto front, new objectives and statistics at each iteration."""
    def __init__(self, instance, statistics, front_generator, verbose=True, assert_results=False):
        # super().__init__(instance, statistics, front_generator, verbose=True)
        self.instance = instance
        self.front_generator_strategy = front_generator
        self.pareto_front = ParetoFront()
        self.verbose = verbose
        self.assert_results = assert_results
        self.statistics = statistics
        self.init_statistics()

    def init_statistics(self):
        self.statistics["pareto_front"] = ""
        self.statistics["solutions_pareto_front"] = ""


    def solve(self):
        for x in self.front_generator_strategy.solve():
            self.add_solution_pareto_front(x)
            self.print_statistics_of_recent_solution(x)
            # todo move asser for model
            # if self.assert_results:
            #     self.assert_solution(x.solution.objs, self.get_selected_images_from_taken(x.solution.taken))
            yield x

    def add_solution_pareto_front(self, solution):
        added_to_front = self.pareto_front.join(solution)
        error = False
        error_msg = (f"Error!! solution {solution} is a new solution which is dominated by some of the previous. "
                     f"Previous solutions: {self.pareto_front.solutions}")
        if not added_to_front and self.front_generator_strategy.always_add_new_solutions_to_front():
            error = True
            print(f"Error!! solution {solution} is a new solution which is dominated by some of the previous")
            print(f"Previous solutions: {self.pareto_front.solutions}")
        self.statistics["pareto_front"] = self.pareto_front.to_str()
        self.statistics["solutions_pareto_front"] = self.pareto_front.solutions_to_str()
        if error:
            raise Exception(error_msg)


    def print_statistics_of_recent_solution(self, solution):
        if self.verbose:
            print("New objective found: " + str(solution["objs"]))
            print(self.statistics["pareto_front"])
            print(self.pareto_front.front_constraint_mzn())
            print(solution.statistics)

    def get_selected_images_from_taken(self, taken):
        selected_images = []
        for idx, taken_image in enumerate(taken):
            if taken_image:
                selected_images.append(idx)
        return selected_images

    def assert_solution(self, solution, selected_images):
        self.assert_cost(selected_images, solution[0])
        self.assert_cloud_covered(selected_images, solution[1])
        self.assert_resolution(selected_images, solution[2])
        self.assert_incidence_angle(selected_images, solution[3])

    def assert_cost(self, selected_images, cost):
        total_cost = 0
        for image in selected_images:
            total_cost += self.instance.costs[image]
        assert total_cost == cost

    def assert_cloud_covered(self, selected_images, cloud_uncovered):
        total_cloud_covered = 0
        cloud_covered = set()
        for image in selected_images:
            if image in self.instance.cloud_covered_by_image:
                for cloud in self.instance.cloud_covered_by_image[image]:
                    if cloud not in cloud_covered:
                        cloud_covered.add(cloud)
                        total_cloud_covered += self.instance.clouds_id_area[cloud]
        total_area_clouds = int(sum(self.instance.clouds_id_area.values()))
        assert total_area_clouds - total_cloud_covered == cloud_uncovered

    def assert_resolution(self, selected_images, resolution):
        calculated_total_resolution = 0
        for element in range(len(self.instance.areas)):
            element_resolution = max(self.instance.resolution)
            for image in selected_images:
                if element in self.instance.images[image]:
                    if self.instance.resolution[image] < element_resolution:
                        element_resolution = self.instance.resolution[image]
            calculated_total_resolution += element_resolution
        assert calculated_total_resolution == resolution

    def assert_incidence_angle(self, selected_images, incidence_angle):
        max_incidence_angle = 0
        for image in selected_images:
            if self.instance.incidence_angle[image] > max_incidence_angle:
                max_incidence_angle = self.instance.incidence_angle[image]
        assert max_incidence_angle == incidence_angle