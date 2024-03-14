from model.mo.FrontGenerators.ByUnsatisfaction import ByUnsatisfaction
from model.mo.FrontGenerators.ImageSpaceDecompositionFeasibleHyperrectangles import UpperBoundConstraintCase
import ast


class TestUnsatisfaction(ByUnsatisfaction):
    def __init__(self, solver, timer, row_with_data):
        super().__init__(solver, timer)
        self.row_with_data = row_with_data
        self.list_with_solutions = self.get_tuple_list_from_solution_panda_row("pareto_front")
        self.solution_counter = 0

    def get_tuple_list_from_solution_panda_row(self, column_name):
        # get the list of solutions from the csv file "file_with_solutions.csv"
        data_str = self.row_with_data[column_name].values[0]
        data_str_formatted = data_str.strip("{}").replace("{", "[").replace("}", "]")
        # Converting the string to a list of tuples
        data_list = ast.literal_eval(data_str_formatted)
        return data_list

    def get_solution_inside_hyperrectangle(self, feasible_hyperrectangle):
        if self.solution_counter < len(self.list_with_solutions):
            solution = self.list_with_solutions[self.solution_counter]
            if not self.is_inside_hyperrectangle(solution, feasible_hyperrectangle):
                # this is an unfeasible rectangle, to have a more precise comparison solve this model also
                formatted_solution, time_to_find_solution = super().get_solution_inside_hyperrectangle(
                    feasible_hyperrectangle)
            else:
                self.solution_counter += 1
                temp_constraints = []
                for i in range(len(self.solver.model.objectives)):
                    temp_constraints.append(self.solver.add_constraints_geq(
                        self.solver.model.objectives[i], feasible_hyperrectangle.lower_corner[i]))
                # constraints due to efficient corners
                if len(feasible_hyperrectangle.efficient_corners) > 0:
                    temp_constraints = self.add_constraints_efficient_corners(
                        feasible_hyperrectangle)
                # constraints smaller than solution
                temp_constraints.extend(self.constraint_solution_space_with_upper_bound_corner(
                    solution, feasible_hyperrectangle.upper_corner, UpperBoundConstraintCase.ALL_OBJECTIVES_SMALLER))
                # solve
                time_to_find_solution = self.get_solver_solution_for_timeout(optimize_not_satisfy=False, verbose=True)
                if self.solver.status_infeasible():
                    formatted_solution = self.prepare_solution_with_data_from_solution_file(solution)
                else:
                    raise ValueError("This should not happen, in this step the solution should be infeasible")
                # remove constraints
        else:
            formatted_solution, time_to_find_solution = super().get_solution_inside_hyperrectangle(
                feasible_hyperrectangle)
        return formatted_solution, time_to_find_solution

    @staticmethod
    def is_inside_hyperrectangle(solution, hyperrectangle):
        solution_tuple = tuple(solution)
        if solution_tuple < hyperrectangle.lower_corner or solution_tuple > hyperrectangle.upper_corner:
            return False
        return True

    def prepare_solution_with_data_from_solution_file(self, solution):
        one_solution = solution
        all_solution_values = self.get_tuple_list_from_solution_panda_row("solutions_pareto_front")
        solution_values = all_solution_values[self.solution_counter - 1]
        formmatted_solution = self.prepare_solution(one_solution, solution_values)
        return formmatted_solution

