from abc import ABC

import constants
from model.mo.Models.GenericModel import GenericModel


class OrtoolsCPModel(GenericModel, ABC):

    def __init__(self):
        self.solution_variables = []
        self.solver_values = []

    def set_solver_name(self):
        self.solver_name = constants.Solver.ORTOOLS_PY.value