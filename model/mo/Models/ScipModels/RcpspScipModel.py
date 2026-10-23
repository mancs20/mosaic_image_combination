from pyscipopt import Model, quicksum

from model.mo.Models.ScipModels.ScipModel import ScipModel
from model.mo.Models.RcpspGenericModel import RcpspGenericModel


class RcpspScipModel(ScipModel, RcpspGenericModel):
    """Time-indexed model of RcpspGenericModel with SCIP."""

    def __init__(self, instance):
        RcpspGenericModel.__init__(self, instance)

    def create_model(self):
        return Model("RcpspScipModel")

    def add_variables_to_model(self):
        self.start = [{t: self.solver_model.addVar(vtype="B", name=f"x_{j}_{t}") for t in self.window(j)}
                      for j in range(self.n_tasks)]

    def linear_expression(self, terms):
        return quicksum(coefficient * variable for coefficient, variable in terms)

    def add_linear_constraint(self, terms, sense, rhs, name):
        expression = self.linear_expression(terms)
        if sense == "<=":
            return self.solver_model.addCons(expression <= rhs, name=name)
        if sense == ">=":
            return self.solver_model.addCons(expression >= rhs, name=name)
        return self.solver_model.addCons(expression == rhs, name=name)

    def review_objective_values(self, objective_values):
        pass

    def start_time(self, j):
        return max(self.start[j], key=lambda t: self.value(self.start[j][t]))
