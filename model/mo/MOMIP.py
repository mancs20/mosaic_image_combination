from model.mo.MO import MO


class MOMIP(MO):

    def __init__(self, instance, statistics, subsolver, verbose=True):
        super().__init__(instance, statistics, subsolver, verbose=True)

    def solve(self):
        return self.econstraint()
        pass

    def econstraint(self):
        # TODO implement here e-constraint method
        pass