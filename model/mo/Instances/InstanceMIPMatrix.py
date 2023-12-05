from model.mo.Instances.InstanceGeneric import InstanceGeneric


class InstanceMIPMatrix(InstanceGeneric):
    def __init__(self, problem_name, objective_matrix, constraints_matrix, rhs_constraints_vector):
        super().__init__(False, problem_name)
        # convert all elements to float
        self.objective_matrix = objective_matrix
        self.constraints_matrix = constraints_matrix
        self.rhs_constraints_vector = rhs_constraints_vector