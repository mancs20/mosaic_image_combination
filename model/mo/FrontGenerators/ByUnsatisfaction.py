from model.mo.FrontGenerators.ImageSpaceDecompositionFeasibleHyperrectangles import \
    ImageSpaceDecompositionFeasibleHyperrectangles, UpperBoundConstraintCase


class ByUnsatisfaction(ImageSpaceDecompositionFeasibleHyperrectangles):
    def __init__(self, solver, timer):
        super().__init__(solver, timer)
        # todo implement the min transormation to be used in maximization models

    def get_solution_inside_hyperrectangle(self, feasible_hyperrectangle):
        found_solution = False
        time_to_find_solution = 0
        formatted_solution = None
        # constraints bigger than lower_bound_corner
        constraints_lower_bound_corner = []
        for i in range(len(self.solver.model.objectives)):
            constraints_lower_bound_corner.append(self.solver.add_constraints_geq(
                self.solver.model.objectives[i], feasible_hyperrectangle.lower_corner[i]))
        # constraints due to efficient corners
        constraints_efficient_corners = []
        if len(feasible_hyperrectangle.efficient_corners) > 0:
            constraints_efficient_corners = self.add_constraints_efficient_corners(
                feasible_hyperrectangle)
        previous_upper_bound_corner = feasible_hyperrectangle.upper_corner
        upper_bound_corner = feasible_hyperrectangle.upper_corner
        case = UpperBoundConstraintCase.ALL_OBJECTIVES_SMALLER
        # todo delete below is for debugging
        intermediate_solution_count = 0
        print(f"Starting to find a solution inside Hyperrectangle: {feasible_hyperrectangle}")
        intermediate_solutions = []
        # todo end delete
        while not found_solution:
            # constraints smaller than upper_bound_corner
            constraints_upper_bound_corner = self.constraint_solution_space_with_upper_bound_corner(
                upper_bound_corner, previous_upper_bound_corner, case)
            # solve
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=False, verbose=True)
            time_to_find_solution += solution_sec
            # todo delete Just for debugging
            intermediate_solution_count += 1
            print(f"Time to get intermediate solution {intermediate_solution_count}: {solution_sec}. "
                  f"Total time: {time_to_find_solution}")
            # todo end delete
            if self.solver.status_infeasible():
                if case == UpperBoundConstraintCase.ALL_OBJECTIVES_SMALLER:
                    case = UpperBoundConstraintCase.AT_LEAST_ONE_OBJECTIVE_SMALLER_THE_REST_EQUAL
                elif (case == UpperBoundConstraintCase.AT_LEAST_ONE_OBJECTIVE_SMALLER_THE_REST_EQUAL or
                      case == UpperBoundConstraintCase.OBJECTIVE_I_SMALLER_THE_REST_EQUAL):
                    found_solution = True
            else:
                formatted_solution = self.prepare_solution()
                previous_upper_bound_corner = upper_bound_corner[:]
                upper_bound_corner = formatted_solution["objs"]
                if case == UpperBoundConstraintCase.AT_LEAST_ONE_OBJECTIVE_SMALLER_THE_REST_EQUAL:
                    case = UpperBoundConstraintCase.OBJECTIVE_I_SMALLER_THE_REST_EQUAL
            # remove constraints smaller than upper_bound_corner
            for i in range(len(constraints_upper_bound_corner)):
                self.solver.remove_constraint(constraints_upper_bound_corner[i])
        # remove temp constraints
        for i in range(len(constraints_lower_bound_corner)):
            self.solver.remove_constraint(constraints_lower_bound_corner[i])
        for i in range(len(constraints_efficient_corners)):
            self.solver.remove_constraint(constraints_efficient_corners[i])
        # todo delete below is for debugging
        print(f"Get a final solution from Hyperrectangle: {feasible_hyperrectangle}")
        # todo end delete
        return formatted_solution, time_to_find_solution

    def get_next_hyperrectangle(self):
        feasible_hyperrectangle = self.possible_feasible_hyperrectangles.pop()
        return feasible_hyperrectangle

    def always_add_new_solutions_to_front(self):
        return True
