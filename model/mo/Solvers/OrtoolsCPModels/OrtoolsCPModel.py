from abc import ABC

import constants
from model.mo.Solvers.GenericModel import GenericModel


class OrtoolsCPModel(GenericModel, ABC):

    def __init__(self, instance):
        self.solution_variables = []
        self.solver_values = []
        super().__init__(instance)

    def set_solver_name(self):
        self.solver_name = constants.Solver.ORTOOLS_PY.value