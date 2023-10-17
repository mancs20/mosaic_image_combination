from abc import ABC

import constants
from model.mo.Solvers.GenericModel import GenericModel


class GurobiModel(GenericModel, ABC):

    def __init__(self, instance):
        super().__init__(instance)

    def set_solver_name(self):
        self.solver_name = constants.Solver.GUROBI.value
