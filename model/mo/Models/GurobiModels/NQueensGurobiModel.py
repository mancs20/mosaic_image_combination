import gurobipy as gp

from model.mo.Instances.InstanceNQueens import InstanceNQueens
from model.mo.Models.GurobiModels.GurobiModel import GurobiModel
from model.mo.Models.NQueensGenericModel import NQueensGenericModel


class NQueensGurobiModel(GurobiModel, NQueensGenericModel):
    """n x n binary variables, queen[i, j] = 1 if a queen is placed on square (i, j). Exactly one queen per row and per
    column (so n queens are placed, as in the CP model with one variable per row) and at most one per diagonal."""

    def review_objective_values(self, objective_values):
        pass

    def add_necessary_solver_configuration(self):
        print("Extra solver configuration no needed")

    def __init__(self, instance: InstanceNQueens):
        NQueensGenericModel.__init__(self, instance)

    def create_model(self):
        return gp.Model("NQueensGurobiModel")

    def get_data_from_instance(self):
        self.n = self.instance.n

    def add_variables_to_model(self):
        self.queen = self.solver_model.addMVar((self.n, self.n), vtype=gp.GRB.BINARY, name="queen")

    def add_constraints_to_model(self):
        n = self.n
        # "== 1" and not "<= 1": the objectives do not count queens, without it boards with less than n queens are
        # feasible (and can be Pareto optimal)
        self.constraints.append(self.solver_model.addConstr(self.queen.sum(axis=1) == 1, name="row"))
        self.constraints.append(self.solver_model.addConstr(self.queen.sum(axis=0) == 1, name="col"))
        # diagonals constraints: for each diagonal, at most one queen can be placed on it. The diagonals are identified by the difference
        for k in range(-n + 1, n):
            self.constraints.append(self.solver_model.addConstr(self.queen.diagonal(k).sum() <= 1, name=f"diag{k}"))
            self.constraints.append(self.solver_model.addConstr(self.queen[:, ::-1].diagonal(k).sum() <= 1,
                                                                name=f"adiag{k}"))

    def define_objectives(self):
        # scalar LinExpr (not MLinExpr): the front generators call getValue() and combine the objectives
        queens = self.queen.tolist()
        for scores in self.instance.score_matrices:
            self.objectives.append(gp.quicksum(scores[i][j] * queens[i][j]
                                               for i in range(self.n) for j in range(self.n)))

    def is_a_minimization_model(self):
        return False

    def get_solution_values(self):
        # column of the queen of each row, the same representation as the CP model
        values = self.queen.X
        return [int(values[i].argmax()) for i in range(self.n)]

    def is_numerically_possible_augment_objective(self):
        return True
