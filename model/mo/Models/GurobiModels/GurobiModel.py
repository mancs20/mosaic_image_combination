from abc import ABC

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


class GurobiModel(GenericModel, ABC):

    def set_solver_name(self):
        self.solver_name = constants.Solver.GUROBI.value
