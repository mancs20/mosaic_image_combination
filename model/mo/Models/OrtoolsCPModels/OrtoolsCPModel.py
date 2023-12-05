from abc import ABC
from typing import Optional

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