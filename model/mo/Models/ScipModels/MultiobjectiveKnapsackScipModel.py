from pyscipopt import Model, quicksum

from model.mo.Instances.InstanceMIPMatrix import InstanceMIPMatrix
from model.mo.Models.ScipModels.ScipModel import ScipModel
from model.mo.Models.MultiobjectiveKnapsackGenericModel import MultiobjectiveKnapsackGenericModel


class MultiobjectiveKnapsackScipModel(ScipModel, MultiobjectiveKnapsackGenericModel):

    def review_objective_values(self, objective_values):
        pass

    def add_necessary_solver_configuration(self):
        print("Extra solver configuration no needed")

    def __init__(self, instance: InstanceMIPMatrix):
        MultiobjectiveKnapsackGenericModel.__init__(self, instance)

    def create_model(self):
        return Model("MultiobjectiveKnapsackScipModel")

    def get_data_from_instance(self):
        self.number_items = len(self.instance.objective_matrix[0])

    def add_variables_to_model(self):
        self.select_item = [self.solver_model.addVar(vtype="B", name=f"select_item_{j}")
                            for j in range(self.number_items)]

    def add_constraints_to_model(self):
        for i in range(len(self.instance.constraints_matrix)):
            weights = self.instance.constraints_matrix[i]
            rhs = self.instance.rhs_constraints_vector[i]
            self.constraints.append(self.solver_model.addCons(quicksum(weights[j] * self.select_item[j]
                                                                       for j in range(self.number_items)) <= rhs))

    def define_objectives(self):
        for i in range(len(self.instance.objective_matrix)):
            self.objectives.append(quicksum(self.instance.objective_matrix[i][j] * self.select_item[j]
                                            for j in range(self.number_items)))

    def is_a_minimization_model(self):
        return False

    def get_solution_values(self):
        return [j for j in range(self.number_items) if self.is_selected(self.select_item[j])]

    def is_numerically_possible_augment_objective(self):
        return True
