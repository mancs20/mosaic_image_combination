from abc import ABC

import constants


class InstanceGeneric(ABC):
    def __init__(self, is_minizinc=True, problem=constants.Problem.SATELLITE_IMAGE_SELECTION_PROBLEM):
        self.problem = problem
        self.is_minizinc = is_minizinc

