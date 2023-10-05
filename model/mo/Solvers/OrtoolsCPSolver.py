import math

from model.mo.Solvers.Solver import Solver
from ortools.sat.python import cp_model
from ortools.sat import sat_parameters_pb2

class OrtoolsCPSolver(Solver, ):
    def __init__(self, instance, statistics, threads, free_search=True):
        super().__init__(instance, statistics, threads, free_search)
        self.status = None
        # variables
        self.select_image = None
        self.cloud_covered = None
        self.cloud_area = None
        self.total_cloudy_area = None
        self.resolution_element = []
        self.total_resolution = None
        self.effective_image_resolution = None
        self.effective_incidence_angle = None
        self.current_max_incidence_angle = None
        # cloud covering
        self.total_area_clouds = int(sum(self.instance.clouds_id_area.values()))
        # objectives
        self.current_objective = None
        self.add_variables()
        self.add_objectives()
        # tackle numerical problems
        self.tackle_numerical_problems()


    def set_model(self):
        return cp_model.CpModel()

    def set_solver(self):
        return cp_model.CpSolver()

    def add_variables(self):
        self.select_image = [self.model.NewBoolVar(f"select_image{i}") for i in range(len(self.instance.images))]
        self.cloud_covered = {}
        self.cloud_area = {}
        for cloud in self.instance.clouds_id_area:
            self.cloud_covered[cloud] = self.model.NewBoolVar(f"cloud_covered{cloud}")
            # self.cloud_covered[cloud] = self.model.NewIntVar(0, len(self.instance.images), f"cloud_covered{cloud}")
            self.cloud_area[cloud] = self.model.NewIntVar(0, self.instance.clouds_id_area[cloud], f"cloud_area{cloud}")

        # todo check if we need more variables

    def add_objectives(self):
        self.objectives = []
        # cloud covered objective
        # todo try with model equivalent to minizinc
        # self.objectives.append(self.model.NewIntVar(0, self.instance.total_area_clouds, "cloud_covered"))
        # total_cloud_covered = self.total_area_clouds - sum(self.cloud_covered[i] * self.instance.clouds_id_area[i]
        #                                         for i in self.instance.clouds_id_area)
        #
        # total_cloud_covered = self.total_area_clouds - sum(self.instance.clouds_id_area[i] for i in
        #                                                    self.instance.clouds_id_area if self.cloud_covered[i] == True)

        self.total_cloudy_area = self.model.NewIntVar(0, self.total_area_clouds, "total_cloudy_area")
        self.model.Add(self.total_cloudy_area == sum(self.cloud_area[i] for i in self.cloud_area))
        self.objectives.append(self.total_cloudy_area)

        # resolution objective
        max_total_resolution = max(self.instance.resolution) * len(self.instance.areas)
        self.total_resolution = self.model.NewIntVar(0, max_total_resolution, "total_resolution")
        self.effective_image_resolution = [self.model.NewIntVar(self.instance.resolution[i], max(self.instance.resolution)+10,
                                                                f"effective_resolution{i}") for i in
                                           range(len(self.instance.images))]
        for i in range(len(self.instance.images)):
            self.model.Add(self.effective_image_resolution[i] == self.instance.resolution[i]).OnlyEnforceIf(self.select_image[i])
            self.model.Add(self.effective_image_resolution[i] == max(self.instance.resolution)+10).OnlyEnforceIf(self.select_image[i].Not())
        for i in range(len(self.instance.areas)):
            self.resolution_element.append(self.model.NewIntVar(0, max(self.instance.resolution), f"resolution{i}"))
            images = self.get_images_covering_element(i)
            self.model.AddMinEquality(self.resolution_element[i], [self.effective_image_resolution[ima] for ima in images])

        self.model.Add(self.total_resolution == sum(self.resolution_element))
        self.objectives.append(self.total_resolution)

        # incidence angle objective
        self.current_max_incidence_angle = self.model.NewIntVar(min(self.instance.incidence_angle),
                                                           max(self.instance.incidence_angle), "max_incidence_angle")
        self.model.AddMaxEquality(self.current_max_incidence_angle,
                                  [self.instance.incidence_angle[i] * self.select_image[i]
                                   for i in range(len(self.instance.images))])

        self.objectives.append(self.current_max_incidence_angle)
        # self.select_image[i] * self.instance.costs[i]
        # self.objectives.append(self.model.NewIntVar(0, sum(self.instance.costs), "cost"))

    def build_objective_e_constraint_saugmecon(self, range_array):
        # ortools cannot work with floats, so we need to convert to ints
        multiply_to_convert_to_int = False
        if multiply_to_convert_to_int:
            gcd = self.gcd(range_array)
            range_array = [int(x/gcd) for x in range_array]
            main_obj_multiplier = 1000
            multiplication_of_range = 1
            for i in range_array:
                main_obj_multiplier *= i
                multiplication_of_range *= i
            multipliers = []
            for i in range(len(range_array)):
                multipliers.append(int(multiplication_of_range / range_array[i]))
            gcd = self.gcd(multipliers + [main_obj_multiplier])
            obj = int(main_obj_multiplier/gcd) * self.get_main_objective()
            constraint_objectives_scaled = []
            for i in range(len(self.objectives)):
                multiplier = multipliers[i]
                lb = self.objectives[i].Proto().domain[0] * multiplier
                up = self.objectives[i].Proto().domain[-1] * multiplier
                constraint_objectives_scaled.append(self.model.NewIntVar(lb, up, f"obj_constraint{i}"))
                self.model.Add(constraint_objectives_scaled[i] == self.objectives[i] * multiplier)
            self.model.Minimize(obj + sum(constraint_objectives_scaled))
        else:
            self.model.Minimize(self.get_main_objective())


    def get_main_objective(self):
        return sum(self.select_image[i] * self.instance.costs[i] for i in range(len(self.select_image)))

    def set_threads(self, threads):
        self.solver.parameters = sat_parameters_pb2.SatParameters(num_search_workers=threads)

    def solve(self, optimize_not_satisfy=True):
        if optimize_not_satisfy:
            self.status = self.solver.Solve(self.model)
            if self.status == cp_model.INFEASIBLE:
                print("infeasible")
        else:
            # todo do satisfiability
            # check https://developers.google.com/optimization/cp/cp_tasks
            pass

    def add_basic_constraints(self):
        # cover constraint
        # constraint forall(u in UNIVERSE)(
        #     exists(i in IMAGES)(taken[i] /\ u in images[i]));
        # for unused_name, tasks in data.groupby("worker"):
        #     self.model.AddAtLeastOne(x[tasks.index])
        for i in range(len(self.instance.areas)):
            images_covering_element = self.get_images_covering_element(i)
            self.model.AddAtLeastOne(self.select_image[j] for j in images_covering_element)
            # self.model.Add(sum(self.select_image[j] for j in self.instance.images[i]) >= 1)

        # incidence angle constraint

        # cloud covered constraint
        # for cloud in self.cloud_area:
        #     potential_images_covering_cloud = self.get_images_covering_element(cloud)
        #     variables = []
        #     for i in potential_images_covering_cloud:
        #         variables.append(self.model.NewBoolVar(f"covering_cloud_{cloud}_by_image_{i}"))
        #     self.model.AddBoolOr(variables).OnlyEnforceIf(self.cloud_covered[cloud])
        #     # self.model.Add(self.cloud_area[cloud] == 0).OnlyEnforceIf(self.cloud_covered[cloud])
        #     self.model.Add(self.cloud_area[cloud] == self.instance.clouds_id_area[cloud]).OnlyEnforceIf(self.cloud_covered[cloud].Not())
        #     # self.model.AddBoolOr([self.model.Not(var) for var in variables]).OnlyEnforceIf(self.cloud_covered[cloud].Not())
        #     # self.model.AddBoolOr(self.cloud_covered[cloud], variables)

        for cloud in self.cloud_area:
            potential_images_covering_cloud = self.get_images_covering_cloud(cloud)
            for i in potential_images_covering_cloud:
                self.model.Add(self.cloud_covered[cloud] == True).OnlyEnforceIf(self.select_image[i])
            self.model.AddAtLeastOne(self.select_image[i] for i in potential_images_covering_cloud).OnlyEnforceIf(self.cloud_covered[cloud])
            # self.model.Add(self.cloud_covered[cloud] == self.model.AddBoolOr([self.select_image[i] for i in potential_images_covering_cloud]))
            # self.model.Add(self.cloud_covered[cloud] == sum(self.select_image[i] for i in potential_images_covering_cloud))
            self.model.Add(self.cloud_area[cloud] == 0).OnlyEnforceIf(self.cloud_covered[cloud])
            self.model.Add(self.cloud_area[cloud] == self.instance.clouds_id_area[cloud]).OnlyEnforceIf(self.cloud_covered[cloud].Not())


    def add_constraints_leq(self, constraint, rhs):
        new_constraint = self.model.Add(constraint <= rhs)
        return new_constraint

    def remove_constraints(self, constraint):
        constraint.Proto().Clear()

    def get_images_covering_element(self, element):
        return [i for i in range(len(self.instance.images)) if element in self.instance.images[i]]

    def get_images_covering_cloud(self, cloud):
        return [i for i in self.instance.cloud_covered_by_image if cloud in self.instance.cloud_covered_by_image[i]]

    def set_minimization(self):
        self.model.Minimize(self.current_objective)

    def set_maximization(self):
        self.model.Maximize(self.current_objective)

    def set_time_limit(self, timeout):
        self.solver.parameters.max_time_in_seconds = timeout

    def set_single_objective(self, objective_expression):
        self.current_objective = objective_expression

    def reset(self):
        return True

    def get_solution_values(self):
        one_solution = [self.solver.Value(self.get_main_objective())]
        for i in range(len(self.objectives)):
            one_solution.append(self.solver.Value(self.objectives[i]))
        one_solution = [int(round(x, 0)) for x in one_solution]
        return one_solution

    def get_selected_images(self):
        selected_images = [index for index in range(len(self.select_image)) if self.solver.Value(self.select_image[index]) == 1]
        return selected_images

    def get_status(self):
        return self.solver.StatusName(self.status)

    def status_time_limit(self):
        return self.status == cp_model.UNKNOWN

    def status_infeasible(self):
        return self.status == cp_model.INFEASIBLE

    def get_complete_solution(self):
        return self.solver

    def get_nodes_solution(self, solution):
        # todo check if this is the best statistic to show
        return self.solver.NumBranches()

    def tackle_numerical_problems(self):
        # self.instance.costs = [int(x/self.gcd(self.instance.costs)) for x in self.instance.costs]
        pass

    def gcd(self, list_to_gcd):
        gcd = list_to_gcd[0]
        for i in range(1, len(list_to_gcd)):
            gcd = math.gcd(gcd, list_to_gcd[i])
        return gcd
