import gurobipy as gp
from gurobipy import *
from minizinc import Solver, Instance
from minizinc import Model as ModelMiniZinc

def main():
    model_mzn = "mosaic_cloud2.mzn"
    data_dzn = "./data_sets/paris_30.dzn"
    images, costs, areas, clouds, max_cloud_area, resolution, incidence_angle = \
        get_data_from_minizinc_dzn(model_mzn, data_dzn, image_id_start=0)

    elements, areas = gp.multidict({i: areas[i] for i in range(len(areas))})

    images_dict = {}
    for i in range(len(images)):
        images_dict[i] = [images[i], costs[i]]
    images_id, images, costs = gp.multidict(images_dict)

    model = gp.Model("mosaic_cloud_mip")
    #decisition variables
    select_image = model.addVars(len(images), vtype=gp.GRB.BINARY, name="select_image_i")
    #constraints
    model.addConstrs(gp.quicksum(select_image[i] for i in images_id if e in images[i]) >= 1 for e in elements)
    #objective function
    model.setObjective(gp.quicksum(select_image[i] * costs[i] for i in images_id), gp.GRB.MINIMIZE)
    #TODO add parameters, like timeout to the model

    model.optimize()

    # return the selected images
    selected_images = []
    for i in images_id:
        if select_image[i].x == 1:
            selected_images.append(i)
    print("Selected images: ", selected_images)

    selected_images_tutorial = []
    for image in select_image.keys():
        if abs(select_image[image].x) > 1e-6:
            selected_images_tutorial.append(image)
    print("Selected images tutorial: ", selected_images_tutorial)

def get_data_from_minizinc_dzn(input_mzn, input_dzn, image_id_start=0):
    model = ModelMiniZinc(input_mzn)
    model.add_file(input_dzn, parse_data=True)
    mzn_solver = Solver.lookup("gecode")
    # config.initialize_cores(mzn_solver)
    # check_already_computed(config)
    instance = Instance(mzn_solver, model)
    images = instance["images"]
    if image_id_start == 0: # Minizinc the id starts at 1
        for i in range (len(images)):
            images[i] = {x - 1 for x in images[i]}
    costs = instance["costs"]
    areas = instance["areas"]
    clouds = instance["clouds"]
    max_cloud_area = instance["max_cloud_area"]
    resolution = instance["resolution"]
    incidence_angle = instance["incidence_angle"]

    return images, costs, areas, clouds, max_cloud_area, resolution, incidence_angle

if __name__ == "__main__":
  main()