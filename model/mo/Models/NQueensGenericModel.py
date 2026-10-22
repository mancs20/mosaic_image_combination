from abc import ABC

from model.mo.Models.GenericModel import GenericModel
import sys
import os

# Get the root directory
from pathlib import Path
script_path = Path(__file__).resolve()
pre_root_dir = script_path.parents[2]
root_dir = os.path.dirname(pre_root_dir)
# Add the root directory to sys.path
sys.path.append(root_dir)
# Import the module from the root directory
import constants


class NQueensGenericModel(GenericModel, ABC):
    """Multi-objective N-Queens (Lukasiewycz et al. 2007): place n non-attacking queens, maximize for each objective
    the sum of the scores of the squares with a queen."""

    def __init__(self, instance):
        self.queen = None
        self.n = 0
        super().__init__(instance)

    def problem_name(self):
        return constants.Problem.MULTI_OBJECTIVE_N_QUEENS_PROBLEM.value

    def is_a_minimization_model(self):
        return False

    def get_nadir_bound_estimation(self):
        # scores are non-negative, so 0 is a lower bound of every objective
        return [0] * len(self.objectives)

    def get_ref_points_for_hypervolume(self):
        return [0] * len(self.objectives)
