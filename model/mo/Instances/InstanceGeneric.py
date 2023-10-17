from abc import ABC

import constants


class InstanceGeneric(ABC):
    def __init__(self, is_minizinc=True, problem_name=constants.Problem.SATELLITE_IMAGE_SELECTION_PROBLEM.value):
        self.problem_name = problem_name
        self.is_minizinc = is_minizinc

