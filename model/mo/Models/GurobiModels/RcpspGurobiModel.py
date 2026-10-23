import gurobipy as gp

from model.mo.Models.GurobiModels.GurobiModel import GurobiModel
from model.mo.Models.RcpspGenericModel import RcpspGenericModel


class RcpspGurobiModel(GurobiModel, RcpspGenericModel):
    """Time-indexed model of RcpspGenericModel with Gurobi."""

    def __init__(self, instance):
        RcpspGenericModel.__init__(self, instance)

    def create_model(self):
        return gp.Model("RcpspGurobiModel")

    def add_variables_to_model(self):
        self.start = [{t: self.solver_model.addVar(vtype=gp.GRB.BINARY, name=f"x_{j}_{t}") for t in self.window(j)}
                      for j in range(self.n_tasks)]

    def linear_expression(self, terms):
        return gp.LinExpr([coefficient for coefficient, _ in terms], [variable for _, variable in terms])

    def add_linear_constraint(self, terms, sense, rhs, name):
        expression = self.linear_expression(terms)
        if sense == "<=":
            return self.solver_model.addConstr(expression <= rhs, name=name)
        if sense == ">=":
            return self.solver_model.addConstr(expression >= rhs, name=name)
        return self.solver_model.addConstr(expression == rhs, name=name)

    def review_objective_values(self, objective_values):
        pass

    def start_time(self, j):
        return max(self.start[j], key=lambda t: self.start[j][t].X)
