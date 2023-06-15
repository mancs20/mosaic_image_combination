from model.mo.MosaicCloudMIPmodel import MosaicCloudMIPmodel
import gurobipy as gp

class MIPModelEConstraintSmallTest(MosaicCloudMIPmodel):

    def add_basic_constraints(self):
        W = [[52,52,28,23,95,69,13,61,32,68],
             [88,98,49,28,43,98,53,52,84,66],
             [57,30,86,50,97,96,59,94,67,14]]
        q = [246,329,325]
        for i in range(3):
            w_row = W[i]
            self.model.addConstr((gp.quicksum(self.select_image[j] * w_row[j] for j in self.images_id)) <= q[i])

    def get_main_objective(self):
        obj_coef = [56,90,34,13,71,33,66,74,88,71]
        return gp.quicksum(self.select_image[i] * obj_coef[i] for i in self.images_id)
    def add_objectives(self):
        self.images_id = gp.tuplelist([i for i in range(10)])
        P = [[54,64,46,37,31,62,52,33,87,35],
             [52,65,58,63,46,66,72,95,42,29]]
        for i in range(2):
            p_row = P[i]
            self.objectives.append(gp.quicksum(self.select_image[j] * p_row[j] for j in self.images_id))
