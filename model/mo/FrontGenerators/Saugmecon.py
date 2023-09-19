import copy

from model.mo.FrontGenerators.FrontGeneratorStrategy import FrontGeneratorStrategy


class Saugmecon(FrontGeneratorStrategy):
    def __init__(self, instance, solver, timer):
        super().__init__(instance, solver, timer)
        self.min_objectives = None
        self.nadir_objectives = None

    def solve(self):
        formatted_solutions, self.min_objectives, self.nadir_objectives = self.initialize_model_with_e_constraint()
        # check if the solver could find the optimum for each objective
        for formatted_solution in formatted_solutions:
            if formatted_solution is not None:
                yield formatted_solution
            else:
                raise TimeoutError()
        # initialize loop-control variables with values equal to the nadir values + 1
        ef_array = [self.nadir_objectives[i] + 1 for i in range(len(self.nadir_objectives))]
        rwv = copy.deepcopy(self.min_objectives)
        previous_solutions = set()
        # add initial objective constraints
        self.solver.add_objective_constraints(ef_array)
        previous_solution_information = []
        # todo saugmecon loop
        self.saugmecon_loop(ef_array, rwv, len(self.min_objectives))

    def saugmecon_loop(self, ef_array, rwv, id_objective):
        id_objective -= 1
        if ef_array[id_objective] > self.min_objectives[id_objective]:
            ef_array[id_objective] -= 1
            if id_objective == 0:
                # solve the saugmecon model
                self.solve_saugmecon_most_innner_loop(ef_array, rwv)
                # todo exit condition when id_objective == 0
            else:
                self.saugmecon_loop(ef_array, rwv, id_objective)
                ef_array[id_objective-1] = self.nadir_objectives[id_objective-1] + 1
                if ef_array[id_objective] > self.min_objectives[id_objective]:
                    ef_array[id_objective] = rwv[id_objective]
                    rwv[id_objective] = self.min_objectives[id_objective]
        else:
            id_objective += 1
            return

    def solve_saugmecon_most_innner_loop(self, ef_array, rwv, id_objective):
        # todo implement this method
        pass

    def initialize_model_with_e_constraint(self):
        formatted_solutions, min_objectives = self.get_min_objectives()
        if None in formatted_solutions:
            return formatted_solutions, min_objectives, None
        nadir_objectives = self.get_nadir_objectives()  # in this case, the nadir is the max
        # prepare the model for the e-constraint method
        self.solver.set_optimization_sense("min")
        range_array = [abs(nadir_objectives[i] - min_objectives[i]) for i in range(len(nadir_objectives))]
        self.solver.optimize_e_constraint_saugmecon(range_array)
        return formatted_solutions, min_objectives, nadir_objectives

    def get_min_objectives(self):
        objectives_values = [0] * len(self.solver.objectives)
        formatted_solutions = [0] * len(self.solver.objectives)
        sense = "min"
        for i in range(len(self.solver.objectives)):
            formatted_solution, objective_val = self.optimize_single_objectives(sense, i)
            objectives_values[i] = objective_val
            formatted_solutions[i] = formatted_solution
            if formatted_solution is None:
                 break
        return formatted_solutions, objectives_values

    def get_nadir_objectives(self):
        nadir_objectives = self.get_upper_bound_nadir()
        return nadir_objectives

    def optimize_single_objectives(self, sense, id_objective):
        objective = self.solver.objectives[id_objective]
        timeout = self.timer.resume()
        print("Start the MIP solver to get the min of objective " + str(id_objective))
        self.solver.set_time_limit(timeout)
        # self.mosaic_model.model.Params.TimeLimit = timeout.total_seconds()
        # self.mosaic_model.model.setObjective(objective, sense)
        # self.mosaic_model.model.optimize()
        self.solver.set_single_objective(objective)
        self.solver.set_optimization_sense(sense)
        self.solver.solve(optimize_not_satisfy=True)

        cp_sec = self.timer.pause()
        print("MIP solver found min of objective " + str(id_objective) + " in " + str(cp_sec) + " seconds")
        # if self.mosaic_model.model.Status == gp.GRB.TIME_LIMIT:
        #     return None, None
        if self.solver.status_time_limit():
            return None, None
        formatted_solution = self.solver.prepare_solution()
        objective_val = formatted_solution['objs'][id_objective+1]
        self.solver.update_statistics(cp_sec)
        self.solver.reset()
        # self.mosaic_model.model.reset(1)
        return formatted_solution, objective_val



