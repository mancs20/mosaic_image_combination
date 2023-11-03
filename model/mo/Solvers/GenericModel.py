from abc import ABC, abstractmethod


class GenericModel(ABC):

    def __init__(self, instance):
        self.instance = instance
        self.assert_right_instance()
        self.solver_model = self.create_model()
        self.solver_name = ""
        self.set_solver_name()
        self.get_data_from_instance()
        self.objectives = []
        self.constraints = []
        self.add_variables()
        self.add_objectives()
        self.add_constraints()

    @abstractmethod
    def create_model(self):
        pass

    @abstractmethod
    def set_solver_name(self):
        pass

    @abstractmethod
    def assert_right_instance(self):
        pass

    def message_incorrect_instance(self):
        return f"Incorrect instance {self.instance} for model {self}"

    @abstractmethod
    def get_data_from_instance(self):
        pass

    @abstractmethod
    def add_variables(self):
        pass

    @abstractmethod
    def add_constraints(self):
        pass

    @abstractmethod
    def add_objectives(self):
        pass

    @abstractmethod
    def get_solution_values(self):
        pass

    def get_nadir_bound_estimation(self):
        return self.instance.get_nadir_bound_estimation()

    def get_ref_points_for_hypervolume(self):
        return self.instance.get_ref_points_for_hypervolume()

    @abstractmethod
    def is_numerically_possible_augment_objective(self):
        pass




