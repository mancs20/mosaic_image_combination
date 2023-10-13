from minizinc import Instance

from model.mo.Instances.InstanceGeneric import InstanceGeneric


class InstanceMinizinc(Instance, InstanceGeneric):
    def __init__(self, solver, model, problem, is_minizinc=False):
        super().__init__(solver, model)
        super().__init__(is_minizinc=True)
