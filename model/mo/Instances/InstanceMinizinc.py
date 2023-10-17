from minizinc import Instance

from model.mo.Instances.InstanceGeneric import InstanceGeneric


class InstanceMinizinc(Instance, InstanceGeneric):
    def __init__(self, solver, model, problem_name):
        super().__init__(solver, model)
        super().__init__(is_minizinc=True, problem_name=problem_name)
