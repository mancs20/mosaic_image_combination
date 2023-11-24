import constants
from model.mo.Solvers.GenericModel import GenericModel


class MinizincPseudoModel(GenericModel):

    def __init__(self):
        self.solver = None
        super().__init__()

    def create_model(self):
        pass

    def set_solver_name(self):
        self.solver_name = constants.Solver.MINIZINC.value

    def assert_right_instance(self):
        pass

    def get_data_from_instance(self):
        pass

    def add_variables(self):
        pass

    def add_constraints(self):
        pass

    def add_objectives(self):
        pass

    def get_solution_values(self):
        return "This is not implemented when using Minizinc"

    def is_numerically_possible_augment_objective(self):
        pass

    def set_solver(self, solver):
        self.solver = solver

    def get_ref_points_for_hypervolume(self):
        return self.solver.solver_solution.solution.ref_point
