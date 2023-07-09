from model.mo.OSolve import OSolve


class OSolveMIP(OSolve):

    def __init__(self, instance, statistics, timer, threads=None, free_search=False):
        super().__init__(instance, statistics, timer, threads, free_search)
    def solve(self):
        pass