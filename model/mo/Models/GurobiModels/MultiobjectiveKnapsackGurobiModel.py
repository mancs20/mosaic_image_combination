import gurobipy as gp

from model.mo.Models.GurobiModels.GurobiModel import GurobiModel
from model.mo.Models.MultiobjectiveKnapsackGenericModel import MultiobjectiveKnapsackGenericModel


class MultiobjectiveKnapsackGurobiModel(GurobiModel, MultiobjectiveKnapsackGenericModel):

    def __init__(self, instance):
        self.select_item = None
        self.number_items = 0
        super().__init__(instance)

    def create_model(self):
        return gp.Model("MultiobjectiveKnapsackGurobiModel")

    def get_data_from_instance(self):
        self.number_items = len(self.instance.objective_matrix[0])

    def add_variables(self):
        self.select_item = self.solver_model.addVars(self.number_items, vtype=gp.GRB.BINARY, name="select_item_i")

    def add_constraints(self):
        for i in range(len(self.instance.constraints)):
            self.constraints.append(gp.quicksum(self.instance.constraints[i][j] * self.select_item[j]
                                                for j in range(self.number_items)) <= self.instance.rhs_constraints_vector[i])

    def add_objectives(self):
        for i in range(len(self.instance.objective_matrix)):
            self.objectives.append(gp.quicksum(self.instance.objective_matrix[i][j] * self.select_item[j]
                                               for j in range(self.number_items)))

    def is_a_minimization_model(self):
        return False

    def get_solution_values(self):
        selected_items = []
        for item in self.select_item:
            if abs(self.select_item[item].x) > 1e-6:
                selected_items.append(item)
        return selected_items

    def is_numerically_possible_augment_objective(self):
        return True