from abc import ABC
from typing import Optional

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
from ortools.sat.python import cp_model


class OrtoolsCPModel(GenericModel, ABC):

    def __init__(self):
        self.solution_variables = []
        self.solver_values = []

    def set_solver_name(self):
        self.solver_name = constants.Solver.ORTOOLS_PY.value

    def create_model(self):
        return cp_model.CpModel()