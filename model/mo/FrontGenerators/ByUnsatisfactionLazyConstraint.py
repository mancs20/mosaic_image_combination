from model.mo.FrontGenerators.ImageSpaceDecompositionFeasibleHyperrectangles import \
    ImageSpaceDecompositionFeasibleHyperrectangles, UpperBoundConstraintCase


class ByUnsatisfactionLazyConstraint(ImageSpaceDecompositionFeasibleHyperrectangles):
    # it seems that it is not speeding up the process, try tomorrow with the right lower bound, also save intermediate solutions in stasts
    # When only one objective has to be reduce, use optimization hint
    def __init__(self, solver, timer):
        super().__init__(solver, timer)
        solver.model.solver_model._vars = solver.model.select_image
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
        if self.solver.lazy_constraints_possible():
            self.solver.use_lazy_constraints = True
        while not found_solution:
            # constraints smaller than upper_bound_corner
            constraints_upper_bound_corner = self.constraint_solution_space_with_upper_bound_corner(
                upper_bound_corner, previous_upper_bound_corner, case)
            # solve
            if case != UpperBoundConstraintCase.OBJECTIVE_I_SMALLER_THE_REST_EQUAL:
                optimize = False
            else:
                optimize = True
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=optimize, verbose=True)
            time_to_find_solution += solution_sec
            # if latest_solution is None, then the problem is infeasible, if not then the problem was feasible and I have to
            # to change the case to AT_LEAST_ONE_OBJECTIVE_SMALLER_THE_REST_EQUAL
            if self.solver.latest_solution is None:
                if case == UpperBoundConstraintCase.ALL_OBJECTIVES_SMALLER or self.solver.status_infeasible():
                    found_solution = True
                else:
                    formatted_solution = self.prepare_solution()
                    previous_upper_bound_corner = upper_bound_corner[:]
                    upper_bound_corner = formatted_solution["objs"]
                    if case == UpperBoundConstraintCase.AT_LEAST_ONE_OBJECTIVE_SMALLER_THE_REST_EQUAL:
                        case = UpperBoundConstraintCase.OBJECTIVE_I_SMALLER_THE_REST_EQUAL
                    elif case == UpperBoundConstraintCase.OBJECTIVE_I_SMALLER_THE_REST_EQUAL:lution = True
            else:
                formatted_solution = self.prepare_solution(
                    self.solver.latest_solution,
                    self.solver.model.get_solution_values(self.solver.latest_values_decision_variables))
                # todo this is to test the atleast one objective smaller uncomment, false value was the original
                test_atleast_one_objective_smaller = True
                if test_atleast_one_objective_smaller:
                    found_solution = True
                else:
                    self.deactivate_callbacks()
                    if case == UpperBoundConstraintCase.ALL_OBJECTIVES_SMALLER:
                        case = UpperBoundConstraintCase.AT_LEAST_ONE_OBJECTIVE_SMALLER_THE_REST_EQUAL
                    upper_bound_corner = formatted_solution["objs"]
            # remove constraints smaller than upper_bound_corner
            for i in range(len(constraints_upper_bound_corner)):
                self.solver.remove_constraint(constraints_upper_bound_corner[i])
        # remove temp constraints
        for i in range(len(constraints_lower_bound_corner)):
            self.solver.remove_constraint(constraints_lower_bound_corner[i])
        for i in range(len(constraints_efficient_corners)):
            self.solver.remove_constraint(constraints_efficient_corners[i])
        return formatted_solution, time_to_find_solution

    def deactivate_callbacks(self):
        self.solver.use_lazy_constraints = False
        self.solver.latest_solution = None
        self.solver.latest_values_decision_variables = None

    def get_next_hyperrectangle(self):
        feasible_hyperrectangle = self.possible_feasible_hyperrectangles.pop()
        return feasible_hyperrectangle

    def always_add_new_solutions_to_front(self):
        return True
