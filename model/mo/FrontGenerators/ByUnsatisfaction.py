from itertools import product

from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy


class ByUnsatisfaction(FrontGeneratorStrategy):
    def __init__(self, solver, timer):
        super().__init__(solver, timer)
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
        feasible_hyperrectangle_solution_space = [(best_estimation_value, worst_estimation_value)]
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

    def get_solution_by_unsatisfaction(self, feasible_hyperrectangle_solution_space):
        found_solution = False
        time_to_find_solution = 0
        formatted_solution = None
        first_iteration = True
        while not found_solution:
            # todo add constraints based on the feasible hyperrectangle solution space
            # constraints bigger than lower_bound_corner
            constraints_lower_bound_corner = []
            for i in range(len(self.solver.model.objectives)):
                constraints_lower_bound_corner.append(self.solver.add_constraints_geq(
                    self.solver.model.objectives[i], feasible_hyperrectangle_solution_space[0][i]))
            # constraints smaller than upper_bound_corner
            or_lhs_constraints_upper_bound_corner = []
            rhs = []
            for i in range(len(self.solver.model.objectives)):
                or_lhs_constraints_upper_bound_corner.append(self.solver.model.objectives[i])
                rhs.append(feasible_hyperrectangle_solution_space[1][i] - 1)
            # todo implement the or constraints
            constraints_upper_bound_corner = self.solver.add_or_constraints_leq(or_lhs_constraints_upper_bound_corner,
                                                                                rhs)
            # solve
            solution_sec = self.get_solver_solution_for_timeout(optimize_not_satisfy=False)
            time_to_find_solution += solution_sec
            if self.solver.status_infeasible() and not first_iteration:
                found_solution = True
            elif first_iteration:
                first_iteration = False
                for constraint in constraints_upper_bound_corner:
                    self.solver.remove_constraint(constraint)
                for i in range(len(self.solver.model.objectives)):
                    constraints_upper_bound_corner.append(self.solver.add_constraints_eq(
                        self.solver.model.objectives[i], feasible_hyperrectangle_solution_space[1][i]))
            else:
                formatted_solution = self.prepare_solution()
                # update upper_bound_corner and constraints
                or_lhs_constraints_upper_bound_corner = []
                rhs = []
                for i in range(len(self.solver.model.objectives)):
                    or_lhs_constraints_upper_bound_corner.append(self.solver.model.objectives[i])
                    rhs.append(formatted_solution["objs"][i] - 1)
                for i in range(len(constraints_upper_bound_corner)):
                    self.solver.remove_constraint(constraints_upper_bound_corner[i])
                constraints_upper_bound_corner = self.solver.add_or_constraints_leq(
                    or_lhs_constraints_upper_bound_corner, rhs)

            # remove temp constraints
            for i in range(len(constraints_lower_bound_corner)):
                self.solver.remove_constraint(constraints_lower_bound_corner[i])
                self.solver.remove_constraint(constraints_upper_bound_corner[i])
        return formatted_solution, time_to_find_solution

    def get_new_hyperrectangles(self, feasible_hyperrectangle, solution_point):
        # todo add points to the new hyperrectangles or constraints, in some cases a wall or an arist of the
        #  hyperrectangle is not allowed
        new_hyperrectangles = []
        lower_bound_corner = feasible_hyperrectangle[0]
        upper_bound_corner = feasible_hyperrectangle[1]

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
            new_hyperrectangles.append((lower_corner, tuple(upper_corner)))
        return new_hyperrectangles

    def always_add_new_solutions_to_front(self):
        return True
