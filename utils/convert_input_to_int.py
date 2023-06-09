from minizinc import Solver, Instance
from minizinc import Model as ModelMiniZinc
from dataclasses import fields

import ProjectDataClasses

def main():
    model_mzn = "../model/mosaic_cloud2.mzn"
    data_dzn = "../model/data_sets/paris_30.dzn"
    output_dzn = "../model/data_sets/integer_values/paris_30_int.dzn"
    convert_to_int_data_values_dzn(model_mzn, data_dzn, output_dzn)

def convert_to_int_data_values_dzn(input_mzn, input_dzn, output_dzn):
    images, costs, areas, clouds, max_cloud_area, resolution, incidence_angle = \
        get_data_from_minizinc_dzn(input_mzn, input_dzn)
    # convert to int
    int_parameters = {field.name:0 for field in fields(ProjectDataClasses.DataSetFieldsForDiscreteApproaches)}
    costs, areas, max_cloud_area, resolution, incidence_angle = \
        convert_to_int(costs, areas, max_cloud_area, resolution, incidence_angle)
    universe_size = len(areas)
    int_parameters["num_images"] = len(images)
    int_parameters["universe"] = universe_size
    int_parameters["images"] = images
    int_parameters["costs"] = costs
    int_parameters["clouds"] = clouds
    int_parameters["areas"] = areas
    int_parameters["max_cloud_area"] = max_cloud_area
    int_parameters["resolution"] = resolution
    int_parameters["incidence_angle"] = incidence_angle

    write_file_dzn_data_file(output_dzn, dict_parameters=int_parameters)

def get_data_from_minizinc_dzn(input_mzn, input_dzn, image_id_start=1):
    model = ModelMiniZinc(input_mzn)
    model.add_file(input_dzn, parse_data=True)
    mzn_solver = Solver.lookup("gecode")
    instance = Instance(mzn_solver, model)
    images = instance["images"]
    costs = instance["costs"]
    areas = instance["areas"]
    clouds = instance["clouds"]
    if image_id_start == 0:  # Minizinc the id starts at 1
        for i in range(len(images)):
            images[i] = {x - 1 for x in images[i]}
        for i in range(len(clouds)):
            clouds[i] = {x - 1 for x in clouds[i]}
    for i in range(len(clouds)):
        if len(clouds[i]) == 0:
            clouds[i] = {}

    max_cloud_area = instance["max_cloud_area"]
    resolution = instance["resolution"]
    incidence_angle = instance["incidence_angle"]

    return images, costs, areas, clouds, max_cloud_area, resolution, incidence_angle

def write_file_dzn_data_file(dzn_file, dict_parameters: dict):
    # iterate over a dictionary to write the dzn file
    with open(dzn_file, 'w') as f:
        for key, value in dict_parameters.items():
            f.write(key + " = " + str(value) + ";\n")

def convert_to_int(costs, areas, max_cloud_area, resolution, incidence_angle):
    costs = [int(x) for x in costs]
    areas = [int(x) for x in areas]
    max_cloud_area = int(max_cloud_area)
    resolution = [int(x * 100) for x in resolution]
    incidence_angle = [int(round(x,1) * 10) for x in incidence_angle]
    return costs, areas, max_cloud_area, resolution, incidence_angle

def convert_to_original_values(resolution, incidence_angle):
    resolution = [x/100 for x in resolution]
    incidence_angle = [x/10 for x in incidence_angle]
    return resolution, incidence_angle

def convert_single_value_to_original(resolution, incidence_angle):
    resolution = resolution/100
    incidence_angle = incidence_angle/10
    return resolution, incidence_angle

if __name__ == "__main__":
  main()