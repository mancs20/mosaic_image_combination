from abc import ABC

from model.mo.Models.GenericModel import GenericModel
import constants


class MultiobjectiveKnapsackGenericModel(GenericModel, ABC):

    def problem_name(self):
        return constants.ProblemName.MULTIOBJECTIVE_KNAPSACK.value

    def is_a_minimization_model(self):
        return False

    def get_nadir_bound_estimation(self):
        nadir_objectives = [0 for i in range(len(self.objectives))]
        return nadir_objectives

    def get_ref_points_for_hypervolume(self):
        ref_points = [0 for i in range(len(self.objectives))]
        return ref_points
