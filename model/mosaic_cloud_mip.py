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
    resolution = gp.tupledict(zip(images_id, resolution))
    # TODO replace this for the epsilon approach
    max_resolution = max(resolution.values())
    min_resolution = min(resolution.values())

    # incidence angle processing
    incidence_angle = gp.tupledict(zip(images_id, incidence_angle))
    # TODO replace this for the epsilon approach
    max_incidence_angle = max(incidence_angle.values())

    model = gp.Model("mosaic_cloud_mip")
    #decisition variables
    select_image = model.addVars(len(images), vtype=gp.GRB.BINARY, name="select_image_i")
    cloud_covered = model.addVars(clouds_id, vtype=gp.GRB.BINARY, name="cloud_covered_e")
    resolution_element = model.addVars(elements, vtype=gp.GRB.CONTINUOUS, name="resolution_element_i")
    effective_image_resolution = model.addVars(len(images), vtype=gp.GRB.CONTINUOUS,
                                               name="effective_resolution_element_i")
    effective_incidence_angle = model.addVars(len(images), vtype=gp.GRB.CONTINUOUS,
                                               name="effective_incidence_angle_i")
    current_max_incidence_angle = model.addVar(vtype=gp.GRB.CONTINUOUS, name="max_allowed_incidence_angle")
    #constraints--------------------------------------------------------------
    # cost constraint
    model.addConstrs(gp.quicksum(select_image[i] for i in images_id if e in images[i]) >= 1 for e in elements)
    # cloud constraint
    model.addConstrs(gp.quicksum(select_image[i] for i in cloud_covered_by_image.keys()
                                 if c in cloud_covered_by_image[i]) >= cloud_covered[c] for c in clouds_id)
    # calculate resolution for each element
    model.addConstrs(((select_image[i] == 0) >> (effective_image_resolution[i] == 2*max_resolution) for i in images_id))
    model.addConstrs(((select_image[i] == 1) >> (effective_image_resolution[i] == resolution[i]) for i in images_id))
    model.addConstrs(resolution_element[e] == gp.min_(effective_image_resolution[i] for i in images_id
                                                      if e in images[i]) for e in elements)
    # constraints end--------------------------------------------------------------

    # # multiobjective constraint with epsilon approach
    # # for cloud coverage
    model.addConstr(gp.quicksum(area_clouds[c] for c in clouds_id) - gp.quicksum(cloud_covered[c] * area_clouds[c] for c in clouds_id) <= max_cloud_area)
    # # for resolution
    model.addConstr(gp.quicksum(resolution_element[e] for e in elements) <= max_resolution * len(elements))
    # # for incidence angle
    model.addConstrs(effective_incidence_angle[i] == select_image[i] * incidence_angle[i] for i in images_id)
    model.addConstr(current_max_incidence_angle == max_(effective_incidence_angle[i] for i in images_id))
    model.addConstr(current_max_incidence_angle <= max_incidence_angle)

    #objective function
    # lexicographical order
    cost_objective = gp.quicksum(select_image[i] * costs[i] for i in images_id)
    cloud_objective = gp.quicksum(area_clouds[c] for c in clouds_id) - \
                      gp.quicksum(cloud_covered[c] * area_clouds[c] for c in clouds_id)
    incidence_angle_objective = current_max_incidence_angle
    resolution_objective = gp.quicksum(resolution_element[e] for e in elements)

    objectives = [cost_objective, cloud_objective, incidence_angle_objective, resolution_objective]
    priority_objectives = [4, 3, 2, 1]

    model.ModelSense = gp.GRB.MINIMIZE

    for i in range(len(objectives)):
        model.setObjectiveN(objectives[i], i, priority_objectives[i])

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



    # Query number of multiple objectives, and number of solutions
    nSolutions = model.SolCount
    nObjectives = model.NumObj
    print('Problem has', nObjectives, 'objectives')
    print('Gurobi found', nSolutions, 'solutions')

    # For each solution, print value of first three variables, and
    # value for each objective function
    solutions = []
    for s in range(nSolutions):
        # Set which solution we will query from now on
        model.params.SolutionNumber = s

        # Print objective value of this solution in each objective
        print('Solution', s, ':', end='')
        for o in range(nObjectives):
            # Set which objective we will query
            model.params.ObjNumber = o
            # Query the o-th objective value
            print(' ', model.ObjNVal, end='')



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