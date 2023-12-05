from model.mo.Instances.InstanceMIPMatrix import InstanceMIPMatrix
from model.mo.Models.MultiobjectiveKnapsackGenericModel import MultiobjectiveKnapsackGenericModel
from model.mo.Models.OrtoolsCPModels.OrtoolsCPModel import OrtoolsCPModel


class MultiobjectiveKnapsackOrtoolsCPModel(OrtoolsCPModel, MultiobjectiveKnapsackGenericModel):

    def __init__(self, instance: InstanceMIPMatrix):
        OrtoolsCPModel.__init__(self)
        MultiobjectiveKnapsackGenericModel.__init__(self, instance)

    def get_data_from_instance(self):
        self.number_items = len(self.instance.objective_matrix[0])

    def add_variables_to_model(self):
        self.select_item = [self.solver_model.NewBoolVar(f"select_item_{i}") for i in range(self.number_items)]
        self.solution_variables.append(self.select_item)

    def add_constraints_to_model(self):
        for i in range(len(self.instance.constraints_matrix)):
            weights = self.instance.constraints_matrix[i]
            weights = [int(w) for w in weights]
            rhs = int(self.instance.rhs_constraints_vector[i])
            self.constraints.append(self.solver_model.Add(sum(weights[j] * self.select_item[j] for j in range(self.number_items)) <= rhs))

    def define_objectives(self):
        for i in range(len(self.instance.objective_matrix)):
            objective_vector = self.instance.objective_matrix[i]
            objective_vector = [int(o) for o in objective_vector]
            objective = self.solver_model.NewIntVar(0, sum(objective_vector), f"objective_{i}")
            self.solver_model.Add(objective == sum(objective_vector[j] * self.select_item[j] for j in range(self.number_items)))
            self.objectives.append(objective)

    def get_solution_values(self):
        selected_items = [index for index in range(len(self.select_item)) if
                           self.solver_values[index] == 1]
        return selected_items

    def is_numerically_possible_augment_objective(self):
        # todo maybe it is possible to do it, but it is necessary to review the method
        #  OrtoolsCPSolver.build_objective_e_constraint_saugmecon when augmentation is True
        return True