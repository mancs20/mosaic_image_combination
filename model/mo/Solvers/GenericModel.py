from abc import ABC, abstractmethod


class GenericModel(ABC):

    def __init__(self, instance):
        self.instance = instance
        self.assert_right_instance()
        self.solver_model = self.create_model()
        self.solver_name = self.set_solver_name()
        self.objectives = []
        self.constraints = []
        # todo maybe is better to create an abstract class for Ortools CP, the values of the solutions need to be accessed
        #  from the solver
        self.solution_variables = []
        self.solver_values = []

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



