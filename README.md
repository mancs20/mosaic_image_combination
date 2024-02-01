## Package dependencies
You need the following packages to be installed:

* [minizinc](https://www.minizinc.org/)
  * `pip install minizinc[dzn] dataclasses-json contextily`
* [gurobi](https://www.gurobi.com/)
  * `pip install gurobipy`
* [Up42 SDK](https://sdk.up42.com/installation/) with plotting functionalities
  * `pip install "up42-py[viz]"`
* [dataclasses-json](https://pypi.org/project/dataclasses-json/)
  * `pip install dataclasses-json`
* [pymoo](https://pymoo.org/)
  * `pip install pymoo`
* [or-tools](https://developers.google.com/optimization/install/python)
  * `pip install ortools`

## Usage

### Download data from UP42
First you need to define the AOI and place it in the aois folder, there is already some examples of AOI in the folder. The AOI files are in GeoJSON format.

To download data from UP42 you need to have an account and an API key. You can find the API key in your profile settings. You can set the API key in the file `config.json` like below:
```json
{
    "project_id": "your_project_id",
    "project_api_key": "your_project_api_key"
}
```
In ProjectDataClasses you can change the search parameters in the dataclass SearchParameters. The search parameters are the following:
* `start_date`: The start date of the search. It is a string in the following format: `YYYY-MM-DD`. Example: `2021-01-01` 
* `end_date`: The end date of the search. It is a string in the following format: `YYYY-MM-DD`. Example: `2023-01-01`
* `collection`: Array of image collection to search for. The default value is `[phr, spot, pneo]`. `phr` is Pleiades High Resolution, `spot` is SPOT 6/7 and `pneo` is Pleiades Neo.
* `cloud_cover`: The maximum cloud cover of the images. It is a float between 0 and 100.
* `limit`: The maximum number of images to return. It is an integer between 1 and 500.

The downloaded data will be stored in the folder `results/aoi_name/search_range_date/number_of_images`, example `results/paris/2021-01-01-2023-01-01/500`.
Inside the folder there will be the following files:
* `images_data.csv`: The metadata of the images in CSV format.
* `images_data.geojson`: The metadata of the images in Geojson format, ready to visualize in a map.
* `search_parameters.json`: The search parameters used to download the images.

### Generate datasets files dzn

To generate the datasets files dzn you need to run the script `main.py`. The script will generate the files in the 
folder `model/data_sets/`. The name of the files follow this rule `aoiName_numberOfImages`, 
example `model/data_sets/paris_30`. 

#### Convert float values in the data set to integers

The data files are initially generated with float values. Due to numerical issues with the solvers a 
conversion to integer values is needed. To convert the float values to integers you need to run the script
`model/utils/convert_input_to_int.py`. The script will convert the float values to int.

### Run the experiments

To run the experiments you need to run the script `model/mo/main.py` with the following arguments:
* `--minizinc_data`: Specify if the data comes from a minizinc data file, 1 is yes 0 is False.
* `--model_mzn`: The path to the mzn model file.
* `--dzn_dir`: The path to the folder with the dzn files.
* `--problem_name`: The name of the problem to solve, Ex: `sims` for the Satellite Image Mosaic Selection Problem 
presented in Constraint Model for the Satellite Image Mosaic Selection Problem. The list of problem names are:
  * `sims`: Satellite Image Mosaic Selection Problem.
  * `mokp`: Multi-objective Knapsack Problem.
* `--solver_name`: The name of the solver to use, `ortools-py`, `gurobi`, etc.
* `--front_strategy`: The strategy to use to generate the Pareto front. Ex: `saugmecon`, `gavanelli`, `gavanelli-opt`.
* `--solver_timeout_sec`: The timeout in seconds for the solver. The experiments were performed with a value of `3600`.
* `--summary`: The path to the summary file. A file with the results of the experiments, generated in CSV format.
* `--cores`: The number of cores to use.
* `--solver_search_strategy`: The strategy to use for the solver. The default value is `free`.
* `--fzn_optimisation_level`: The optimisation level for the fzn file. The default value is `1`.
* `--instance_name`: The name of the instance to run the experiment, for example `paris_30` for `sims`. For `mokp` 
the names are in the form `augmecon2_<number_objectives>kp<number_items>` for example `augmecon2_3kp40` for 3 
objectives and constraints and 40 items. 

Example:
```bash
python main.py --minizinc_data 1 --model_mzn ../mosaic_cloud2.mzn --dzn_dir ../data_sets/ --problem_name sims --solver_name gurobi --front_strategy saugmecon --solver_timeout_sec 3600 --summary ../summary_test_sims_2_cost_cloud.csv --cores 6 --solver_search_strategy free --fzn_optimisation_level 1 --instance_name paris_30
```

#### Results
The result file is a CSV file generated inside the folder `model/mo`. The file `summary.csv` has the results used in the 
work **"Constraint Model for the Satellite Image Mosaic Selection Problem"**, presented in the **"The 29th International 
Conference on Principles and Practice of Constraint Programming"**. The description of the columns of the file are 
presented below:
* `instance`: The name of the instance. Example: `paris_30`.
* `problem`: The name of the problem. Example: `sims`.
* `solver_name`: The name of the solver used. Example: `gurobi`.
* `front_strategy`: The strategy used to generate the Pareto front. Example: `saugmecon`.
* `solver_search_strategy`: The strategy used by the solver. Values: `free`, the default search strategy of the solver or 
`greedy` the proposed search strategy inspired in the well-know greedy approach for set covering problems.
* `fzn_optimisation_level`: The optimisation level used by the solver. Only used by the cp solvers.
* `threads`: The number of threads used by the solver.
* `cores`: The number of cores used by the solver.
* `solver_timeout_sec`: The timeout in seconds used by the solver to run the experiment.
* `minizinc_model`: The name of the minizinc model used. Values: `mosaic_cloud2` or `mosaic_cloud3`. The first one implements the
default search strategy of the solver and the second one implements the proposed search strategy. It is is neccessary to read
* minizinc data files and when minizinc is used to solve the model.
* `exhaustive`: A value of `TRUE` means that the whole Pareto front was obtained.
* `hypervolume`: The hypervolume of the Pareto front found by the solver.
* `datetime`: The date and time when the experiment was performed.
* `number_of_solutions`: The number of all the solutions found by the solver, not only the solutions that belong to the Pareto
front, but all the intermediate solutions.
* `total_nodes`: The total number of nodes explored by the solver.
* `time_solver_sec`: The time in seconds used by the solver.
* `minizinc_time_fzn_sec`: The time in seconds used by the solver to generate the fzn file. Only valid if minizinc was used.
* `hypervolume_current_solutions`: The hypervolume of the Pareto front found by the solver at each iteration. It has the same amount of values as the number of solutions found by the solver (`solutions_time_list`).
* `solutions_time_list`: The time in which each solution was found by the solver.
* `pareto_solutions_time_list`: The time in which each solution that belongs to the Pareto front was found by the solver.
* `pareto_front`: A list with the objective values of the solutions that belong to the Pareto.
* `solutions_pareto_front`: A list with the image ids selected for the solutions that belong to the Pareto front.
* `incomplete_timeout_solution_added_to_front`: A value of `TRUE` means that if the solver couldn't finish in the given time, the last incomplete solution (the solver couldn't find or prove the optimum for that case) was added to the front.








