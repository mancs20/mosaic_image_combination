import re
import sys
import os

# Get the root directory
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
# Add the root directory to sys.path
sys.path.append(root_dir)
# Import the module from the root directory
import constants

from model.mo.Instances.InstanceGeneric import InstanceGeneric


class InstanceRCPSP(InstanceGeneric):
    """RCPSP with makespan and weighted earliness-tardiness (rcpsp-wet-mkspan.mzn). Read from the MiniZinc data, tasks
    and resources are 0-based here (1-based in the data)."""

    def __init__(self, minizinc_data):
        super().__init__(is_minizinc=False, problem_name=constants.Problem.RCPSP_WET_MAKESPAN_PROBLEM.value)
        self.n_resources = minizinc_data["n_res"]
        self.capacities = list(minizinc_data["rc"])
        self.n_tasks = minizinc_data["n_tasks"]
        self.durations = list(minizinc_data["d"])
        self.requirements = self.read_array2d(minizinc_data["rr"])  # requirements[r][j]
        self.successors = [sorted(k - 1 for k in successors) for successors in minizinc_data["suc"]]
        deadline = self.read_array2d(minizinc_data["deadline"])  # deadline[j] = [due date, earliness cost, tardiness cost]
        self.due_dates = [row[0] for row in deadline]
        self.earliness_costs = [row[1] for row in deadline]
        self.tardiness_costs = [row[2] for row in deadline]
        # as in the MiniZinc model: start times in 0..t_max - 1 and the makespan is the start of the last task
        self.t_max = sum(self.durations)

    @staticmethod
    def read_array2d(value):
        """The MiniZinc Python parser returns array2d(1..n, 1..m, [...]) unparsed (as text): list of n rows."""
        if isinstance(value, list):
            return [list(row) for row in value]
        match = re.fullmatch(r"\s*array2d\(\s*(\d+)\.\.(\d+)\s*,\s*(\d+)\.\.(\d+)\s*,\s*\[(.*)\]\s*\)\s*", str(value),
                             re.S)
        if match is None:
            raise ValueError(f"Cannot read the 2d array {str(value)[:100]}")
        rows = int(match.group(2)) - int(match.group(1)) + 1
        columns = int(match.group(4)) - int(match.group(3)) + 1
        values = [int(x) for x in match.group(5).split(",") if x.strip()]
        if len(values) != rows * columns:
            raise ValueError(f"The 2d array has {len(values)} values, expected {rows} x {columns}")
        return [values[i * columns:(i + 1) * columns] for i in range(rows)]
