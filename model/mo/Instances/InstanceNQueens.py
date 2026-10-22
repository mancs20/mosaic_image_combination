from model.mo.Instances.InstanceGeneric import InstanceGeneric


class InstanceNQueens(InstanceGeneric):
    """Multi-objective N-Queens: an n x n board and one score matrix (n x n) per objective."""
    def __init__(self, problem_name, n, score_matrices):
        super().__init__(False, problem_name)
        self.n = n
        self.score_matrices = score_matrices  # score_matrices[p][i][j]: score of square (i, j) for objective p
