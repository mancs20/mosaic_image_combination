from abc import ABC

import constants
from model.mo.Models.GenericModel import GenericModel


class GurobiModel(GenericModel, ABC):

    def set_solver_name(self):
        self.solver_name = constants.Solver.GUROBI.value
