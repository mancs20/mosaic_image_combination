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

    # clouds processing
    cloud_covered_by_image = {}
    clouds_id_area = {}
    for i in range(len(clouds)):
        image_cloud_set = clouds[i]
        for cloud_id in image_cloud_set:
            if cloud_id not in clouds_id_area:
                clouds_id_area[cloud_id] = areas[cloud_id]
            for j in range(len(images)):
                if i != j:
                    if cloud_id in images[j] and cloud_id not in clouds[j]: # the area of the cloud is covered by image j, and it is not cloudy in j
                        if j in cloud_covered_by_image:
                            cloud_covered_by_image[j].add(cloud_id)
                        else:
                            cloud_covered_by_image[j] = {cloud_id}

    cloud_covered_by_image = gp.tupledict(cloud_covered_by_image)
    clouds_id, area_clouds = gp.multidict(clouds_id_area)

    # resolution processing
    resolution = gp.tupledict(resolution)
    # TODO replace this for the epsilon approach
    max_resolution = max(resolution.values())

    # incidence angle processing
    incidence_angle = gp.tupledict(incidence_angle)
    # TODO replace this for the epsilon approach
    max_incidence_angle = max(incidence_angle.values())

    model = gp.Model("mosaic_cloud_mip")
    #decisition variables
    select_image = model.addVars(len(images), vtype=gp.GRB.BINARY, name="select_image_i")
    cloud_covered = model.addVars(clouds_id, vtype=gp.GRB.BINARY, name="cloud_covered_e")
    #constraints--------------------------------------------------------------
    # cost constraint
    model.addConstrs(gp.quicksum(select_image[i] for i in images_id if e in images[i]) >= 1 for e in elements)
    # cloud constraint
    model.addConstrs(gp.quicksum(select_image[i] for i in images_id if c in cloud_covered_by_image[i])
                     >= cloud_covered[c] for c in clouds_id)
    # multiobjective constraint with epsilon approach
    # for cloud coverage
    model.addConstrs(gp.quicksum(area_clouds[c] for c in clouds_id) -
                     gp.quicksum(cloud_covered[c] * area_clouds[c] for c in clouds_id) <= max_cloud_area)
    # for resolution
    # model.addConstrs(gp.quicksum(select_image[i] * areas[i] for i in images_id) <= max_resolution)
    # for incidence angle
    model.addConstrs(select_image[i]*incidence_angle[i] <= max_incidence_angle for i in images_id)
    # constraints end--------------------------------------------------------------
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

if __name__ == "__main__":
  main()