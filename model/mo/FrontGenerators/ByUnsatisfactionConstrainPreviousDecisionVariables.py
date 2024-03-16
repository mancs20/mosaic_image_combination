from model.mo.FrontGenerators.ImageSpaceDecompositionFeasibleHyperrectangles import \
    ImageSpaceDecompositionFeasibleHyperrectangles, UpperBoundConstraintCase


class ByUnsatisfactionConstrainPreviousDecisionVariables(ImageSpaceDecompositionFeasibleHyperrectangles):
    def __init__(self, solver, timer):
        super().__init__(solver, timer)
        # todo implement the min transormation to be used in maximization models

    def get_solution_inside_hyperrectangle(self, feasible_hyperrectangle):
        found_solution = False
        time_to_find_solution = 0
        formatted_solution = None
        # constraints bigger than lower_bound_corner
        permanent_constraints_for_hyperrectangle = []
        # constraints due to efficient corners
        if len(feasible_hyperrectangle.efficient_corners) > 0:
            permanent_constraints_for_hyperrectangle = self.add_constraints_efficient_corners(
                feasible_hyperrectangle)
        for i in range(len(self.solver.model.objectives)):
            permanent_constraints_for_hyperrectangle.append(self.solver.add_constraints_geq(
                self.solver.model.objectives[i], feasible_hyperrectangle.lower_corner[i]))
        previous_upper_bound_corner = feasible_hyperrectangle.upper_corner
        upper_bound_corner = feasible_hyperrectangle.upper_corner
        case = UpperBoundConstraintCase.ALL_OBJECTIVES_SMALLER
        # todo delete below is for debugging
        intermediate_solution_count = 0
        print(f"Starting to find a solution inside Hyperrectangle: {feasible_hyperrectangle}")
        intermediate_solutions = []
        hints = None
        # todo end delete
        while not found_solution:
            # constraints smaller than upper_bound_corner
            temp_constraints = self.constraint_solution_space_with_upper_bound_corner(
                upper_bound_corner, previous_upper_bound_corner, case)
            # solve
            if formatted_solution is not None:
                # todo complete this
                boolean_variables = self.solver.model.select_image
                boolean_variable_values = self.get_decision_variables_values_from_solution(formatted_solution,
                                                                                           boolean_variables)
                permanent_constraints_for_hyperrectangle.append(self.solver.add_at_least_one_bool_different(boolean_variables, boolean_variable_values))
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=False, verbose=True, hint=hints)
            time_to_find_solution += solution_sec
            # todo delete Just for debugging
            intermediate_solution_count += 1
            print(f"Time to get intermediate solution {intermediate_solution_count}: {solution_sec}. "
                  f"Total time: {time_to_find_solution}")
            # todo end delete
            if self.solver.status_infeasible():
                if case == UpperBoundConstraintCase.ALL_OBJECTIVES_SMALLER:
                    # todo add hint from previous solution for this case
                    # # todo generalize this now I'm harcoding the variable
                    # selected_images = [0] * len(self.solver.model.select_image)
                    # hints = []
                    # for i in range(len(formatted_solution["solution_values"])):
                    #     selected_images[formatted_solution["solution_values"][i]] = 1
                    # hint = [self.solver.model.select_image, selected_images]
                    # hints.append(hint)
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
            for i in range(len(temp_constraints)):
                self.solver.remove_constraint(temp_constraints[i])
        # remove temp constraints
        for i in range(len(permanent_constraints_for_hyperrectangle)):
            self.solver.remove_constraint(permanent_constraints_for_hyperrectangle[i])
        # todo delete below is for debugging
        print(f"Get a final solution from Hyperrectangle: {feasible_hyperrectangle}")
        # todo end delete
        return formatted_solution, time_to_find_solution

    def get_next_hyperrectangle(self):
        feasible_hyperrectangle = self.possible_feasible_hyperrectangles.pop()
        return feasible_hyperrectangle
    
    def get_decision_variables_values_from_solution(self, formatted_solution, variables):
        boolean_variable_values = [0] * len(variables)
        for i in range(len(formatted_solution["solution_values"])):
            boolean_variable_values[formatted_solution["solution_values"][i]] = 1
        return boolean_variable_values

    def always_add_new_solutions_to_front(self):
        return True
