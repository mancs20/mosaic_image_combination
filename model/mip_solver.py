import copy
import csv

import gurobipy as gp
from gurobipy import *
from minizinc import Solver, Instance
from minizinc import Model as ModelMiniZinc
import time

from model.mo.MosaicCloudMIPmodel import MosaicCloudMIPmodel


def main():
    model_mzn = "mosaic_cloud2.mzn"
    data_dzn = "./data_sets/paris_30.dzn"
    get_pareto_front_e_constraint(model_mzn, data_dzn)

def get_pareto_front_e_constraint(model_mzn, data_dzn):
    images, costs, areas, clouds, max_cloud_area, resolution, incidence_angle = \
        get_data_from_minizinc_dzn(model_mzn, data_dzn, image_id_start=0)

    decimals = 3
    costs, areas, max_cloud_area, resolution, incidence_angle = round_values(costs, areas, max_cloud_area, resolution,
                                                                             incidence_angle, decimals=decimals)

    cloud_covered_by_image, clouds_id_area = get_clouds_covered_by_image(clouds, images, areas)
    mosaic_model = MosaicCloudMIPmodel(images, costs, areas, cloud_covered_by_image, clouds_id_area, max_cloud_area,
                                       resolution, incidence_angle, model=gp.Model("mosaic_cloud_mip"),
                                       multiply_to_convert_to_integers=10**decimals)
    # add basic constraints
    mosaic_model.add_basic_constraints()
    # find min and nadir for each objective
    # cost_objective, cloud_objective, resolution_objective, incidence_angle_objective
    min_objectives = get_min_objectives(mosaic_model, main_objective_id=0)
    nadir_objectives = get_nadir_objectives(mosaic_model) # in this case, the nadir is the max
    # prepare the model for the e-constraint method
    mosaic_model.model.ModelSense = gp.GRB.MINIMIZE





    # # TODO: Delete after checking that is working for the cost objective----------------------
    # # ----------------------------------------------------------------------------------------
    # mosaic_model.model.setObjective(gp.quicksum(mosaic_model.select_image[i] * mosaic_model.costs[i]
    #                                             for i in mosaic_model.images_id))
    # mosaic_model.model.optimize()
    # selected_images = get_selected_images(mosaic_model)
    # print("Selected images ", selected_images)
    # # TODO: Delete after checking that is working for the cost objective----------------------
    # # ----------------------------------------------------------------------------------------





    range_array = [nadir_objectives[i] - min_objectives[i] for i in range(len(nadir_objectives))]
    mosaic_model.optimize_e_constraint(range_array)
    start_time = time.time()
    solutions_values, selected_images_for_solution_i = get_pareto_saugmencon_cycle(mosaic_model,
                                                                                   min_objectives, nadir_objectives)
    end_time = time.time()
    execution_time = end_time - start_time
    write_values_to_file(solutions_values, selected_images_for_solution_i, execution_time)

def get_clouds_covered_by_image(clouds, images, areas):
    cloud_covered_by_image = {}
    clouds_id_area = {}
    for i in range(len(clouds)):
        image_cloud_set = clouds[i]
        for cloud_id in image_cloud_set:
            if cloud_id not in clouds_id_area:
                clouds_id_area[cloud_id] = areas[cloud_id]
            for j in range(len(images)):
                if i != j:
                    if cloud_id in images[j] and cloud_id not in clouds[
                        j]:  # the area of the cloud is covered by image j, and it is not cloudy in j
                        if j in cloud_covered_by_image:
                            cloud_covered_by_image[j].add(cloud_id)
                        else:
                            cloud_covered_by_image[j] = {cloud_id}
    return cloud_covered_by_image, clouds_id_area

def get_min_objectives(mosaic_model, main_objective_id):
    return optimize_single_objectives(mosaic_model, GRB.MINIMIZE)

def get_nadir_objectives(mosaic_model):
    return optimize_single_objectives(mosaic_model, GRB.MAXIMIZE)

def optimize_single_objectives(mosaic_model, sense):
    objectives_values = [0] * len(mosaic_model.objectives)
    for i in range(len(mosaic_model.objectives)):
        objective = mosaic_model.objectives[i]
        mosaic_model.model.setObjective(objective, sense)
        # TODO add parameters, like timeout to the model
        mosaic_model.model.optimize()
        objectives_values[i] = mosaic_model.model.objVal
    return objectives_values

def get_pareto_saugmencon_cycle(mosaic_model, min_objectives, nadir_objectives):
    # initialize loop-control variables with values equal to the nadir values + 1
    ef_array = [nadir_objectives[i] + 1 for i in range(len(nadir_objectives))]
    # rwv = [0] * len(nadir_objectives)
    rwv = copy.deepcopy(min_objectives)
    solutions_values = []
    selected_images_for_solution_i = []
    # rwv[2] = min_objectives[2]
    while ef_array[2] > min_objectives[2]:
        ef_array[2] -= 1
        # rwv[1] = min_objectives[1]
        while ef_array[1] > min_objectives[1]:
            ef_array[1] -= 1
            while ef_array[0] > min_objectives[0]:
                ef_array[0] -= 1
                mosaic_model.add_objective_constraints(ef_array)
                # TODO add parameters, like timeout to the model
                mosaic_model.model.optimize()
                if mosaic_model.model.Status == gp.GRB.INFEASIBLE:
                    ef_array = exit_from_loop_with_acceleration(ef_array, nadir_objectives, min_objectives)
                else:
                    # record the solution
                    one_solution = [mosaic_model.get_main_objective().getValue()]
                    for i in range(len(mosaic_model.objectives)):
                        if type(mosaic_model.objectives[i]) == gp.Var:
                            one_solution.append(mosaic_model.objectives[i].x)
                        else:
                            one_solution.append(mosaic_model.objectives[i].getValue())
                    selected_images_for_solution_i.append(get_selected_images(mosaic_model))
                    ef_array[0] = one_solution[1] # one_solution[0] is the main objective
                    # Explore the relatively worst values rwv of objectives
                    rwv = explore_new_relatively_worst_values_of_objectives(rwv, one_solution)
                    # Transform the solution values dividing by the multiplier to convert to integer
                    for i in range(1, len(one_solution)):
                        one_solution[i] = one_solution[i] / mosaic_model.multiply_to_convert_to_integers
                    solutions_values.append(one_solution)
            ef_array[0] = nadir_objectives[0] + 1
            if ef_array[1] > min_objectives[1]:
                ef_array[1] = rwv[1]
                rwv[1] = min_objectives[1]
        ef_array[1] = nadir_objectives[1] + 1
        if ef_array[2] > min_objectives[2]:
            ef_array[2] = rwv[2]
            rwv[2] = min_objectives[2]
    return solutions_values, selected_images_for_solution_i


def exit_from_loop_with_acceleration(ef_array, nadir_objectives, min_objectives):
    i = 0
    while i < (len(ef_array) - 1) and ef_array[i] == nadir_objectives[i]:
        i += 1
    # TODO FIX FOR J WHEN IS EQUAL TO 0
    for j in range(i+1):
        ef_array[j] = min_objectives[j]
    return ef_array

def explore_new_relatively_worst_values_of_objectives(rwv, one_solution):
    # one_solution[0] is the main objective
    for i in range(len(rwv)):
        if one_solution[i+1] > rwv[i]:
            rwv[i] = one_solution[i+1]
    return rwv

def get_selected_images(mosaic_model):
    # return the selected images
    # selected_images = []
    # for i in images_id:
    #     if select_image[i].x == 1:
    #         selected_images.append(i)
    # print("Selected images: ", selected_images)

    selected_images = []
    for image in mosaic_model.select_image.keys():
        if abs(mosaic_model.select_image[image].x) > 1e-6:
            selected_images.append(image)
    # print("Selected images tutorial: ", selected_images)
    return selected_images



    # Query number of multiple objectives, and number of solutions
    # nSolutions = model.SolCount
    # nObjectives = model.NumObj
    # print('Problem has', nObjectives, 'objectives')
    # print('Gurobi found', nSolutions, 'solutions')
    #
    # # For each solution, print value of first three variables, and
    # # value for each objective function
    # solutions = []
    # for s in range(nSolutions):
    #     # Set which solution we will query from now on
    #     model.params.SolutionNumber = s
    #
    #     # Print objective value of this solution in each objective
    #     print('Solution', s, ':', end='')
    #     for o in range(nObjectives):
    #         # Set which objective we will query
    #         model.params.ObjNumber = o
    #         # Query the o-th objective value
    #         print(' ', model.ObjNVal, end='')

def get_data_from_minizinc_dzn(input_mzn, input_dzn, image_id_start=0):
    model = ModelMiniZinc(input_mzn)
    model.add_file(input_dzn, parse_data=True)
    mzn_solver = Solver.lookup("gecode")
    # config.initialize_cores(mzn_solver)
    # check_already_computed(config)
    instance = Instance(mzn_solver, model)
    images = instance["images"]
    costs = instance["costs"]
    areas = instance["areas"]
    clouds = instance["clouds"]
    if image_id_start == 0: # Minizinc the id starts at 1
        for i in range (len(images)):
            images[i] = {x - 1 for x in images[i]}
        for i in range (len(clouds)):
            clouds[i] = {x - 1 for x in clouds[i]}
    max_cloud_area = instance["max_cloud_area"]
    resolution = instance["resolution"]
    incidence_angle = instance["incidence_angle"]

    return images, costs, areas, clouds, max_cloud_area, resolution, incidence_angle

def round_values(costs, areas, max_cloud_area, resolution, incidence_angle, decimals):
    costs = [round(x, decimals) for x in costs]
    areas = [round(x, decimals) for x in areas]
    resolution = [round(x, decimals) for x in resolution]
    incidence_angle = [round(x, decimals) for x in incidence_angle]
    max_cloud_area = round(max_cloud_area, decimals)
    return costs, areas, max_cloud_area, resolution, incidence_angle

def write_values_to_file(solutions_values, selected_images_for_solution_i, execution_time):
    values = []
    for i in range(len(selected_images_for_solution_i)):
        arr = [selected_images_for_solution_i[i]]
        for j in range(len(solutions_values[i])):
            arr.append(solutions_values[i][j])
        values.append(arr)

    output_file = "solutions.csv"
    with open(output_file, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Execution time", execution_time])
        writer.writerow(["Selected Images", "Cost", "Cloud Coverage", "Resolution", "Incidence Angle"])
        writer.writerows(values)

    print(f"Values saved in {output_file} successfully.")

if __name__ == "__main__":
  main()