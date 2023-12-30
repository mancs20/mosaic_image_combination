from abc import ABC



class InstanceGeneric(ABC):
    def __init__(self, is_minizinc, problem_name):
        self.problem_name = problem_name
        self.is_minizinc = is_minizinc

