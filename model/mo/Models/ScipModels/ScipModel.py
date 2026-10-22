from abc import ABC, abstractmethod

import sys
import os

# Get the root directory
from pathlib import Path
script_path = Path(__file__).resolve()
pre_root_dir = script_path.parents[3]
root_dir = os.path.dirname(pre_root_dir)
# Add the root directory to sys.path
sys.path.append(root_dir)
# Import the module from the root directory
import constants

from model.mo.Models.GenericModel import GenericModel


class ScipModel(GenericModel, ABC):
    # a binary or integer variable is considered selected when its value is above this threshold
    SELECTED_THRESHOLD = 0.5

    def set_solver_name(self):
        self.solver_name = constants.Solver.SCIP.value

    @abstractmethod
    def review_objective_values(self, objective_values):
        pass

    def value(self, variable_or_expression):
        """Value in the best solution of the last solve."""
        return self.solver_model.getVal(variable_or_expression)

    def is_selected(self, variable):
        return self.value(variable) > ScipModel.SELECTED_THRESHOLD
