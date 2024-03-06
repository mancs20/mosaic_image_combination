from enum import Enum
from itertools import product

from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy


class ByUnsatisfaction(FrontGeneratorStrategy):
    def __init__(self, solver, timer):
        super().__init__(solver, timer)
        self.id_constraint_or = 0
        # todo implement the min transormation to be used in maximization models

    def solve(self):
        # get the first efficient solution
        yield from self.get_solutions()

    def get_solutions(self):
        # check if it is a minimization or maximization model
        if not self.solver.model.is_a_minimization_model():
            raise NotImplementedError("This method is only implemented for minimization models so far.")
        # add the initial feasible hyperrectangle solution space, delimited by the worst and best estimation values
        best_estimation_value = tuple(self.get_ideal_objectives())
        worst_estimation_value = tuple(self.get_nadir_objectives())
        feasible_hyperrectangle_solution_space = [Hyperrectangle(best_estimation_value, worst_estimation_value)]
        while len(feasible_hyperrectangle_solution_space) > 0:
            # select the hyperrectangle region to be explored
            feasible_hyperrectangle = feasible_hyperrectangle_solution_space.pop()  # todo implement several methods to select the hyperrectangle later
            # get the solution by unsatisfaction
            solution, time_to_find_solution = self.get_solution_by_unsatisfaction(feasible_hyperrectangle)
            # if there is no solution, continue to the next hyperrectangle
            if solution is not None:
                self.solver.update_statistics(time_to_find_solution)
                yield solution
                # define new hyperrectangle solution spaces, which is equal to 2^p - 2, where p is the number of
                # objectives. The 2 discarded hyperrectangles are the ones that are completely dominated by the solution
                # and the one that completely dominates the solution. In the first one any solutions that is found is
                # going to be dominated by the solution, and in the second one, is in the infeasible region, is
                # impossible to find a solution that dominates an efficient solution (Pareto front)
                solution_point = tuple(solution["objs"])
                new_hyperrectangles = self.get_new_hyperrectangles(feasible_hyperrectangle, solution_point)
                # add the new hyperrectangles to the feasible hyperrectangle solution space
                feasible_hyperrectangle_solution_space.extend(new_hyperrectangles)

    def get_new_hyperrectangles(self, feasible_hyperrectangle, solution_point):
        # todo add points to the new hyperrectangles or constraints, in some cases a wall or an arist of the
        #  hyperrectangle is not allowed
        new_hyperrectangles = []
        lower_bound_corner = feasible_hyperrectangle.lower_corner
        upper_bound_corner = feasible_hyperrectangle.upper_corner

        ranges_new_lower_corners = [(lower_bound_corner[i], solution_point[i]) for i in range(len(solution_point))]
        new_lower_corners = list(product(*ranges_new_lower_corners))
        # remove the lower_bound_corner and the solution_point from the new_lower_corners
        for i in range(len(new_lower_corners)):
            if new_lower_corners[i] == lower_bound_corner:
                new_lower_corners.pop(i)
                break
        for i in range(len(new_lower_corners) - 1, -1, -1):
            if new_lower_corners[i] == solution_point:
                new_lower_corners.pop(i)
                break

        for lower_corner in new_lower_corners:
            upper_corner = [0] * len(solution_point)
            for i in range(len(upper_corner)):
                if lower_corner[i] == solution_point[i]:
                    upper_corner[i] = upper_bound_corner[i]
                else:
                    upper_corner[i] = solution_point[i]
            upper_corner = tuple(upper_corner)
            # create the new hyperrectangle and add the efficient corners (points that belong to the Pareto front)
            efficient_corners = [solution_point]
            # if the feasible_hyperrectangle had efficient corners, add them if they belong to the new hyperrectangle
            for efficient_corner in feasible_hyperrectangle.efficient_corners:
                if lower_corner <= efficient_corner <= upper_corner:
                    efficient_corners.append(efficient_corner)
            new_hyperrectangles.append(Hyperrectangle(lower_corner, upper_corner, efficient_corners))
        return new_hyperrectangles

    def get_solution_by_unsatisfaction(self, feasible_hyperrectangle_solution_space):
        found_solution = False
        time_to_find_solution = 0
        formatted_solution = None
        # constraints bigger than lower_bound_corner
        constraints_lower_bound_corner = []
        for i in range(len(self.solver.model.objectives)):
            constraints_lower_bound_corner.append(self.solver.add_constraints_geq(
                self.solver.model.objectives[i], feasible_hyperrectangle_solution_space.lower_corner[i]))
        # constraints due to efficient corners
        constraints_efficient_corners = []
        if len(feasible_hyperrectangle_solution_space.efficient_corners) > 0:
            constraints_efficient_corners = self.add_constraints_efficient_corners(
                feasible_hyperrectangle_solution_space)
        previous_upper_bound_corner = feasible_hyperrectangle_solution_space.upper_corner
        upper_bound_corner = feasible_hyperrectangle_solution_space.upper_corner
        case = UpperBoundConstraintCase.ALL_OBJECTIVES_SMALLER
        while not found_solution:
            # constraints smaller than upper_bound_corner
            constraints_upper_bound_corner = self.constraint_solution_space_with_upper_bound_corner(
                upper_bound_corner, previous_upper_bound_corner, case)
            # solve
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=False)
            time_to_find_solution += solution_sec
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
        return formatted_solution, time_to_find_solution

    def add_constraints_efficient_corners(self, feasible_hyperrectangle_solution_space):
        constraints_efficient_corners = []
        for efficient_corner in feasible_hyperrectangle_solution_space.efficient_corners:
            rhs = [efficient_corner[i] - 1 for i in range(len(efficient_corner))]
            temp_constraints = self.add_chained_constraints_leq_with_or(
                self.solver.model.objectives, rhs)
            constraints_efficient_corners.extend(temp_constraints)
        return constraints_efficient_corners

    def constraint_solution_space_with_upper_bound_corner(self, upper_bound_corner, previous_upper_bound_corner, case):
        if case == UpperBoundConstraintCase.ALL_OBJECTIVES_SMALLER:
            return self.constraint_solution_space_all_objectives_smaller_ub(upper_bound_corner)
        elif case == UpperBoundConstraintCase.AT_LEAST_ONE_OBJECTIVE_SMALLER_THE_REST_EQUAL:
            return self.constraint_solution_space_at_least_one_objective_smaller_the_rest_equal_ub(
                upper_bound_corner)
        elif case == UpperBoundConstraintCase.OBJECTIVE_I_SMALLER_THE_REST_EQUAL:
            return self.constraint_solution_space_obj_i_smaller_the_rest_equal_ub(upper_bound_corner,
                                                                                  previous_upper_bound_corner)

    def constraint_solution_space_all_objectives_smaller_ub(self, upper_bound_corner):
        constraints_upper_bound_corner = []
        for i in range(len(self.solver.model.objectives)):
            constraints_upper_bound_corner.append(self.solver.add_constraints_leq(
                self.solver.model.objectives[i], upper_bound_corner[i]-1))
        return constraints_upper_bound_corner

    def constraint_solution_space_at_least_one_objective_smaller_the_rest_equal_ub(self, upper_bound_corner):
        constraints_upper_bound_corner = []
        for i in range(len(self.solver.model.objectives)):
            constraints_upper_bound_corner.append(self.solver.add_constraints_leq(
                self.solver.model.objectives[i], upper_bound_corner[i]))
        # constraint at least one objective smaller
        rhs = [upper_bound_corner[i] - 1 for i in range(len(upper_bound_corner))]
        constraints_upper_bound_corner.extend(self.add_chained_constraints_leq_with_or(
            self.solver.model.objectives, rhs))
        return constraints_upper_bound_corner

    def constraint_solution_space_obj_i_smaller_the_rest_equal_ub(self, upper_bound_corner,
                                                                  previous_upper_bound_corner):
        constraints_upper_bound_corner = []
        for i in range(len(upper_bound_corner)):
            if upper_bound_corner[i] < previous_upper_bound_corner[i]:
                constraints_upper_bound_corner.append(self.solver.add_constraints_leq(
                    self.solver.model.objectives[i], upper_bound_corner[i] - 1))
            else:
                constraints_upper_bound_corner.append(self.solver.add_constraints_eq(
                    self.solver.model.objectives[i], upper_bound_corner[i]))
        return constraints_upper_bound_corner

    def add_chained_constraints_leq_with_or(self, constraints_lhs, rhs):
        constraints = self.solver.chained_constraints_leq_with_or(constraints_lhs, rhs)
        self.id_constraint_or += 1
        return constraints

    def always_add_new_solutions_to_front(self):
        return True


class Hyperrectangle:
    def __init__(self, lower_corner, upper_corner, efficient_corners=[]):
        self.lower_corner = lower_corner
        self.upper_corner = upper_corner
        self.efficient_corners = efficient_corners


class UpperBoundConstraintCase(Enum):
    ALL_OBJECTIVES_SMALLER = 1
    AT_LEAST_ONE_OBJECTIVE_SMALLER_THE_REST_EQUAL = 2
    OBJECTIVE_I_SMALLER_THE_REST_EQUAL = 3
    # ALL_OBJECTIVES_EQUAL =
