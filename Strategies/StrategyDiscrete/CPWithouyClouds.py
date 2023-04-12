from Strategies.StrategyDiscrete.StrategyDiscrete import StrategyDiscrete
from minizinc import Instance, Model, Result, Solver, Status
import multiprocessing


class CPWithoutClouds(StrategyDiscrete):
    path = ""
    model_path = "./model/mosaic_no_cloud.mzn"
    name = "Constraint_Programming_Discrete_Without_Clouds"
    number_of_runs = 1

    def run_strategy(self):
        super().discretize()
        results = self.initialize_result()
        selected_image_id = self.get_solution_from_minizinc_solver(self.get_minizinc_instance_model())
        for image_id in selected_image_id:
            results = results.append(self.images.loc[self.images["image_id"] == image_id])
        return self.prepare_results_to_return(results)

    def initialize_model_parameters(self, instance):
        instance["images"] = len(self.sets_images)
        instance["universe"] = self.universe
        instance["sets"] = [set(x.list_of_regions) for x in self.sets_images]
        instance["costs"] = [x.weight for x in self.sets_images]

    def get_minizinc_instance_model(self, minizinc_solver="gecode"):
        solver = Solver.lookup(minizinc_solver)
        model = Model(self.model_path)
        instance = Instance(solver, model)
        self.initialize_model_parameters(instance)
        return instance

    def get_solution_from_minizinc_solver(self, instance):
        cores = multiprocessing.cpu_count() * 2
        solution = instance.solve(optimisation_level=3, free_search=True, processes=cores)
        cover = [image_idx for image_idx, take_image in enumerate(solution["taken"]) if take_image]
        return cover
