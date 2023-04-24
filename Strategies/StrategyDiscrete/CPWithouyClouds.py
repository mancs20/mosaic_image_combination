from Strategies.StrategyDiscrete.StrategyDiscrete import StrategyDiscrete
from Strategies.StrategyDiscrete.SolverMinizinc import SolverMinizinc


class CPWithoutClouds(StrategyDiscrete, SolverMinizinc):
    @property
    def model_path(self):
        return "./model/mosaic_no_cloud.mzn"

    path = ""
    name = "Constraint_Programming_Discrete_Without_Clouds"
    number_of_runs = 1

    def run_strategy(self):
        super().discretize()
        return self.get_results_from_cp_solver()

    def get_results_from_cp_solver(self):
        results = self.initialize_result()
        results = self.get_transformed_solutions(results=results, images=self.images, sets_images=self.sets_images,
                                                 universe=self.universe)
        return self.prepare_results_to_return(results)

    def initialize_model_parameters(self, instance):
        instance["images"] = len(self.sets_images)
        instance["universe"] = self.universe
        instance["sets"] = self.get_sets()
        instance["costs"] = [x.weight for x in self.sets_images]

    def get_sets(self):
        sets = []
        for x in self.sets_images:
            regions_ids = []
            for region in x.list_of_regions:
                regions_ids.append(region.id)
            sets.append(set(regions_ids))
        return sets

    # def get_minizinc_instance_model(self, minizinc_solver="gecode"):
    #     solver = Solver.lookup(minizinc_solver)
    #     model = Model(self.model_path)
    #     instance = Instance(solver, model)
    #     self.initialize_model_parameters(instance)
    #     return instance
    #
    # def get_solution_from_minizinc_solver(self, instance):
    #     cores = multiprocessing.cpu_count() * 2
    #     solution = instance.solve(optimisation_level=3, free_search=True, processes=cores)
    #     cover = [image_idx for image_idx, take_image in enumerate(solution["taken"]) if take_image]
    #     return cover
