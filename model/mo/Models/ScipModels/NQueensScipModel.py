from pyscipopt import Model, quicksum

from model.mo.Instances.InstanceNQueens import InstanceNQueens
from model.mo.Models.ScipModels.ScipModel import ScipModel
from model.mo.Models.NQueensGenericModel import NQueensGenericModel


class NQueensScipModel(ScipModel, NQueensGenericModel):
    """Same model as NQueensGurobiModel: n x n binary variables, queen[i][j] = 1 if a queen is placed on square (i, j).
    Exactly one queen per row and per column and at most one per diagonal."""

    def review_objective_values(self, objective_values):
        pass

    def add_necessary_solver_configuration(self):
        print("Extra solver configuration no needed")

    def __init__(self, instance: InstanceNQueens):
        NQueensGenericModel.__init__(self, instance)

    def create_model(self):
        return Model("NQueensScipModel")

    def get_data_from_instance(self):
        self.n = self.instance.n

    def add_variables_to_model(self):
        self.queen = [[self.solver_model.addVar(vtype="B", name=f"queen_{i}_{j}") for j in range(self.n)]
                      for i in range(self.n)]

    def add_constraints_to_model(self):
        n = self.n
        # "== 1" and not "<= 1": the objectives do not count queens, without it boards with less than n queens are
        # feasible (and can be Pareto optimal)
        for i in range(n):
            self.constraints.append(self.solver_model.addCons(quicksum(self.queen[i][j] for j in range(n)) == 1,
                                                              name=f"row{i}"))
        for j in range(n):
            self.constraints.append(self.solver_model.addCons(quicksum(self.queen[i][j] for i in range(n)) == 1,
                                                              name=f"col{j}"))
        # diagonals constraints: for each diagonal, at most one queen can be placed on it. Diagonal k has the squares
        # (i, i + k), anti-diagonal k the squares (i, n - 1 - (i + k)), like diagonal(k) of the Gurobi matrix API
        for k in range(-n + 1, n):
            rows = [i for i in range(n) if 0 <= i + k < n]
            self.constraints.append(self.solver_model.addCons(quicksum(self.queen[i][i + k] for i in rows) <= 1,
                                                              name=f"diag{k}"))
            self.constraints.append(self.solver_model.addCons(quicksum(self.queen[i][n - 1 - (i + k)]
                                                                       for i in rows) <= 1, name=f"adiag{k}"))

    def define_objectives(self):
        for scores in self.instance.score_matrices:
            self.objectives.append(quicksum(scores[i][j] * self.queen[i][j]
                                            for i in range(self.n) for j in range(self.n)))

    def is_a_minimization_model(self):
        return False

    def get_solution_values(self):
        # column of the queen of each row, the same representation as the CP model
        return [max(range(self.n), key=lambda j: self.value(self.queen[i][j])) for i in range(self.n)]

    def is_numerically_possible_augment_objective(self):
        return True
