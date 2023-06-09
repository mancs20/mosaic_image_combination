import time
from abc import ABC, abstractmethod
import os

from minizinc import Instance, Model, Solver
import multiprocessing

from utils.convert_input_to_int import write_file_dzn_data_file


class SolverMinizinc(ABC):
    @property
    @abstractmethod
    def model_path(self):
        pass

    def get_transformed_solutions(self, results, images, sets_images, universe, minizinc_parameters: dict):
        # save the time that the self.get_solution_from_minizinc_solver takes to run
        instance = self.get_minizinc_instance_model(minizinc_parameters)
        start_time = time.time()
        solution = SolverMinizinc.get_solution_from_minizinc_solver(instance)
        end_time = time.time()
        execution_time = end_time - start_time
        print("Time to run the solver in seconds: ", execution_time)
        selected_image_id, status = self.process_solution(solution)
        for image_set_id in selected_image_id:
            results = results.append(images[images["image_id"] == sets_images[image_set_id].image_id])
        results["time_in_seconds"] = execution_time
        results["size_universe"] = universe
        results["solution_status"] = status
        return results

    @staticmethod
    def process_solution(solution):
        cover = [image_idx for image_idx, take_image in enumerate(solution["taken"]) if take_image]
        status = solution.status.name
        print("Solution objective: ", str(solution.objective))
        return cover, status

    @staticmethod
    def initialize_model_parameters(instance, minizinc_parameters: dict):
        for key, value in minizinc_parameters.items():
            instance[key] = value

    def get_minizinc_instance_model(self, minizinc_parameters: dict, minizinc_solver="gecode"):
        solver = Solver.lookup(minizinc_solver)
        model = Model(self.model_path)
        instance = Instance(solver, model)
        self.initialize_model_parameters(instance, minizinc_parameters)
        return instance

    @staticmethod
    def get_solution_from_minizinc_solver(instance):
        cores = multiprocessing.cpu_count() * 2
        solution = instance.solve(optimisation_level=1, free_search=False, processes=cores)
        return solution

    @abstractmethod
    def solver_minizinc_parameters(self) -> dict:
        pass

    @staticmethod
    def dzn_filename(aoi_name, number_images_per_aoi, cloud_name):
        from Experiment import Experiment
        base_path = "./model/data_sets/"
        aoi_name, range_dates, number_images_per_aoi = Experiment.define_unique_name_for_file_folder(aoi_name,
                                                                                                     number_images_per_aoi)
        dzn_file = base_path + aoi_name + "_" + range_dates + "_" + cloud_name + "_" + number_images_per_aoi + ".dzn"
        return dzn_file

    @staticmethod
    def dzn_file_exists(dzn_file_name):
        # check if the dzn file exists
        return os.path.isfile(dzn_file_name)

    @staticmethod
    def write_dzn_file(dzn_file, dict_parameters: dict):
        write_file_dzn_data_file(dzn_file, dict_parameters)

    @staticmethod
    def add_new_parameter_to_dzn_file(dzn_file, dict_parameters: dict):
        with open(dzn_file, 'a') as f:
            for key, value in dict_parameters.items():
                f.write(key + " = " + str(value) + ";\n")