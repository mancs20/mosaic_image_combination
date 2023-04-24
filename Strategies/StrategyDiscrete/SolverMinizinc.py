import time
from abc import ABC, abstractmethod
from minizinc import Instance, Model, Result, Solver, Status
import multiprocessing

class SolverMinizinc(ABC):
    @property
    @abstractmethod
    def model_path(self):
        pass

    def get_transformed_solutions(self, results, images, sets_images, universe):
        # save the time that the self.get_solution_from_minizinc_solver takes to run
        start_time = time.time()
        solution = SolverMinizinc.get_solution_from_minizinc_solver(self.get_minizinc_instance_model())
        end_time = time.time()
        selected_image_id, status = self.process_solution(solution)
        execution_time = end_time - start_time
        print("Time to run the solver in seconds: ", execution_time)
        for image_set_id in selected_image_id:
            results = results.append(images[images["image_id"] == sets_images[image_set_id].image_id])
        results["time_in_seconds"] = execution_time
        results["size_universe"] = universe
        results["solution_status"] = status
        return results

    def process_solution(self, solution):
        cover = [image_idx for image_idx, take_image in enumerate(solution["taken"]) if take_image]
        status = solution.status.name
        return cover, status

    @abstractmethod
    def initialize_model_parameters(self, instance):
        pass

    def get_minizinc_instance_model(self, minizinc_solver="gecode"):
        solver = Solver.lookup(minizinc_solver)
        model = Model(self.model_path)
        instance = Instance(solver, model)
        self.initialize_model_parameters(instance)
        return instance

    @staticmethod
    def get_solution_from_minizinc_solver(instance):
        cores = multiprocessing.cpu_count() * 2
        solution = instance.solve(optimisation_level=3, free_search=True, processes=cores)
        return solution