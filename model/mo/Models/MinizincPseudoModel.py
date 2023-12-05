import constants
from model.mo.Models.GenericModel import GenericModel


class MinizincPseudoModel(GenericModel):

    def __init__(self):
        self.solver = None
        super().__init__()

    def problem_name(self):
        return "Not defined for Minizinc"

    def assert_right_instance(self, instance):
        print("Instance checking is done in Minizinc, everything should be fine :)")

    def create_model(self):
        pass

    def set_solver_name(self):
        self.solver_name = constants.Solver.MINIZINC.value

    def get_data_from_instance(self):
        pass

    def add_variables_to_model(self):
        pass

    def add_constraints_to_model(self):
        pass

    def define_objectives(self):
        pass

    def is_a_minimization_model(self):
        print("Maximization is not implemented so far, when using Minizinc be aware that the model will be treated as a "
              "minimization model")
        return True

    def get_solution_values(self):
        return "This is not implemented when using Minizinc"

    def is_numerically_possible_augment_objective(self):
        pass

    def set_solver(self, solver):
        self.solver = solver

    def get_ref_points_for_hypervolume(self):
        return self.solver.solver_solution.solution.ref_point
