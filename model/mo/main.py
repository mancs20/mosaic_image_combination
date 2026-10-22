import sys
import os
import json
import ast

# Get the root directory
from pathlib import Path

script_path = Path(__file__).resolve()
pre_root_dir = script_path.parents[1]
root_dir = os.path.dirname(pre_root_dir)
# Add the root directory to sys.path
sys.path.append(root_dir)
# Import the module from the root directory
import constants

from Config import *
from MOCP import *
from Timer import *
from minizinc import Instance, Model, Solver
import csv
import traceback
import logging
from filelock import FileLock, Timeout

from model.mo.MOWithFrontGenerator import MOWithFrontGenerator
from model.mo.FrontGenerators.Gavanelli import Gavanelli
from model.mo.FrontGenerators.Saugmecon import Saugmecon
from model.mo.FrontGenerators.CoverageGridPoint import CoverageGridPoint
from model.mo.Instances.InstanceMIPMatrix import InstanceMIPMatrix
from model.mo.Instances.InstanceMinizinc import InstanceMinizinc
from model.mo.Instances.InstanceNQueens import InstanceNQueens
from model.mo.Instances.InstanceSIMS import InstanceSIMS
from model.mo.Models.GurobiModels.MultiobjectiveKnapsackGurobiModel import MultiobjectiveKnapsackGurobiModel
from model.mo.Models.GurobiModels.NQueensGurobiModel import NQueensGurobiModel
from model.mo.Models.GurobiModels.SatelliteImageMosaicSelectionGurobiModel import \
    SatelliteImageMosaicSelectionGurobiModel
from model.mo.Models.OrtoolsCPModels.MultiobjectiveKnapsackOrtoolsCPModel import MultiobjectiveKnapsackOrtoolsCPModel
from model.mo.Solvers.GurobiSolver import GurobiSolver
from model.mo.Models.MinizincPseudoModel import MinizincPseudoModel
from model.mo.Solvers.MinizincSolver import MinizincSolver
from model.mo.Models.OrtoolsCPModels.SatelliteImageMosaicSelectionOrtoolsCPModel import \
    SatelliteImageMosaicSelectionOrtoolsCPModel
from model.mo.Solvers.OrtoolsCPSolver import OrtoolsCPSolver


def init_top_level_statistics(statistics):
    statistics["exhaustive"] = False
    statistics["hypervolume"] = 0
    statistics["datetime"] = datetime.now()


def init_solution_details_statistics(statistics):
    statistics["number_of_solutions"] = 0
    statistics["total_nodes"] = 0
    statistics["time_solver_sec"] = 0  # Time spent in the solver.
    statistics["minizinc_time_fzn_sec"] = 0
    statistics["hypervolume_current_solutions"] = []
    statistics["solutions_time_list"] = []
    statistics["pareto_solutions_time_list"] = []
    statistics["pareto_front"] = ""
    statistics["solutions_pareto_front"] = ""
    statistics["incomplete_timeout_solution_added_to_front"] = False


def main():
    config = Config()
    if not config.bench_mode:  # in bench mode the campaign (parallel --resume) decides what is already computed
        check_already_computed(config)
    instance = build_instance(config)
    print("Start computing: " + config.uid())
    statistics = {}
    config.init_statistics(statistics)
    init_top_level_statistics(statistics)
    model = build_model(instance, config)
    solver, pareto_front = build_solver(model, instance, config, statistics)
    search_start = datetime.now()
    save_results = True
    try:
        statistics["exhaustive"] = False
        statistics["incomplete_timeout_solution_added_to_front"] = False
        for x in solver.solve():
            pass
        print("Problem completely explored.")
        statistics["exhaustive"] = True
    except TimeoutError:
        print("Timeout triggered getting last incomplete solution")
        if solver.process_last_incomplete_solution():
            # the last incomplete solution was added to the pareto front
            print("Last incomplete solution added to the pareto front")
            statistics["incomplete_timeout_solution_added_to_front"] = True
        else:
            print("There were not incomplete solution or the last incomplete solution was not added to "
                  "the pareto front")
            set_right_time_after_timeout(statistics, config.solver_timeout_sec)
    except Exception as e:
        print("Error Execption raised: " + str(e))
        logging.error(traceback.format_exc())
        save_results = False
    # wall-clock time of the whole search (solver and the Python work around it)
    statistics["time_total_sec"] = (datetime.now() - search_start).total_seconds()
    if save_results:
        statistics["all_solutions"] = statistics["all_solutions"][:-1]
        statistics["all_solutions"] += "}"
        statistics["hypervolume"] = pareto_front.hypervolume()
        pareto_solutions_time_list = [statistics["solutions_time_list"][x] for x in pareto_front.front]
        statistics["pareto_solutions_time_list"] = pareto_solutions_time_list
        print("end of solving statistics: " + str(statistics))
        write_statistics(config, statistics)
        print_bench_json_protocol(config, statistics, pareto_front)


def set_right_time_after_timeout(statistics, config_timeout_sec):
    statistics["time_solver_sec"] = config_timeout_sec


def build_instance(config):
    instance = None
    if config.bench_mode:
        return build_instance_bench(config)
    if use_minizinc_data(config):
        instance = build_instance_minizinc_data(config)
    else:
        config.initialize_cores(solver=None, check_solver=False)
        instance = build_instance_text_data(config)

    return instance


def build_instance_bench(config):
    """Bench mode: everything is derived from the instance path (see Config.init_data_files_from_bench_instance_path)."""
    config.initialize_cores(solver=None, check_solver=False)
    if config.minizinc_data:
        # Only the data is needed: Gurobi is called directly, not through MiniZinc.
        model = Model(config.input_mzn)
        model.add_file(config.input_dzn, parse_data=True)
        if config.problem_name.startswith("sims"):
            return InstanceSIMS(model)
    elif config.problem_name == "ukp":
        objective_matrix, constraints_matrix, rhs_constraints_vector = read_moolibrary_ukp_dat(config.input_dzn)
        return InstanceMIPMatrix(constants.Problem.MULTI_OBJECTIVE_KNAPSACK_PROBLEM.value, objective_matrix,
                                 constraints_matrix, rhs_constraints_vector)
    elif config.problem_name == constants.Problem.MULTI_OBJECTIVE_N_QUEENS_PROBLEM.value:
        n, score_matrices = read_n_queens_dat(config.input_dzn)
        return InstanceNQueens(constants.Problem.MULTI_OBJECTIVE_N_QUEENS_PROBLEM.value, n, score_matrices)
    print(f"Error: problem {config.problem_name} with instance {config.instance_path} is not supported in bench mode")
    sys.exit(1)


def read_moolibrary_ukp_dat(file_path):
    """MOOLibrary UKP .dat: number of objectives p, number of items n, capacity, p rows of profits (one list
    literal), and the row of weights."""
    with open(file_path, 'r') as file:
        lines = [line.strip() for line in file if line.strip()]
    if lines[0].startswith("#"):
        raise NotImplementedError("vOptLib .dat files are not supported yet, only MOOLibrary UKP")
    number_objectives, number_items, capacity = int(lines[0]), int(lines[1]), int(lines[2])
    profits = ast.literal_eval(" ".join(lines[3:3 + number_objectives]))
    weights = ast.literal_eval(lines[3 + number_objectives])
    assert len(profits) == number_objectives and all(len(row) == number_items for row in profits)
    assert len(weights) == number_items
    return profits, [weights], [capacity]


def read_n_queens_dat(file_path):
    """Multi-objective N-Queens .dat: number of objectives p, number of queens n, then p score matrices n x n."""
    with open(file_path, 'r') as file:
        numbers = [int(value) for value in file.read().split()]
    number_objectives, n = numbers[0], numbers[1]
    scores = numbers[2:]
    assert len(scores) == number_objectives * n * n, f"{file_path}: expected {number_objectives} matrices {n}x{n}"
    score_matrices = [[scores[(p * n + i) * n:(p * n + i + 1) * n] for i in range(n)]
                      for p in range(number_objectives)]
    return n, score_matrices


def use_minizinc_data(config) -> bool:
    return config.minizinc_data == True


def build_instance_minizinc_data(config):
    # here we build the instance, it could from minizinc or from other format
    model = Model(config.input_mzn)
    model.add_file(config.input_dzn, parse_data=True)
    if config.solver_name == "gurobi":
        mzn_solver = Solver.lookup("gurobi")
    else:
        mzn_solver = Solver.lookup(config.solver_name)
    config.initialize_cores(mzn_solver)
    instance = Instance(mzn_solver, model)
    problem_name = config.problem_name
    if config.solver_name == "gurobi" or config.solver_name == "ortools-py":
        if problem_name in (constants.Problem.SATELLITE_IMAGE_SELECTION_PROBLEM.value,
                            "sims_cost_clouds",
                            "sims_cost_clouds_angle"):
            instance = InstanceSIMS(instance)
    else:
        instance = InstanceMinizinc(mzn_solver, model, problem_name)

    return instance


def build_instance_text_data(config):
    objective_matrix = []
    constraints_matrix = []
    rhs_constraints_vector = []
    if config.problem_name == constants.Problem.MULTI_OBJECTIVE_KNAPSACK_PROBLEM.value:
        datasets_folder = os.path.join(config.data_sets_folder, "mokp",
                                       config.data_name)
        path_objective_matrix, path_constraints_matrix, path_rhs_constraints_vector = \
            mokp_get_text_data_files(datasets_folder, config.data_name)
        objective_matrix = mokp_get_matrix_from_file(path_objective_matrix)
        constraints_matrix = mokp_get_matrix_from_file(path_constraints_matrix)
        rhs_constraints_vector = mokp_get_rhs_vector_from_file(path_rhs_constraints_vector)
    else:
        print("Error: problem name not recognized")
        sys.exit(1)
    instance = InstanceMIPMatrix(config.problem_name, objective_matrix, constraints_matrix, rhs_constraints_vector)
    return instance


def mokp_get_text_data_files(datasets_folder, data_name):
    # data_name is in the form 3kp40, get first character and the ones after kp two characters
    kp_index = data_name.find("kp")
    number_objs = data_name[:kp_index]
    number_items = data_name[kp_index + 2:]

    path_objective_matrix = os.path.join(datasets_folder, f"z{number_objs}_{number_items}ctt.txt")
    path_constraints_matrix = os.path.join(datasets_folder, f"z{number_objs}_{number_items}att.txt")
    path_rhs_constraints_vector = os.path.join(datasets_folder, f"z{number_objs}_{number_items}btt.txt")
    return path_objective_matrix, path_constraints_matrix, path_rhs_constraints_vector


def mokp_get_matrix_from_file(file_path, file_has_headers=True):
    # Read the file and extract data
    with open(file_path, 'r') as file:
        lines = file.readlines()
    if file_has_headers:
        # Remove the first row and first column headers
        rows = [line.strip().split('\t')[1:] for line in lines[1:]]
    else:
        rows = [line.strip().split('\t') for line in lines]
    rows = [[float(value) for value in row] for row in rows]
    number_of_columns = len(rows[0])
    matrix = []
    for column in range(number_of_columns):
        complete_column = [row[column] for row in rows]
        matrix.append(complete_column)
    return matrix


def mokp_get_rhs_vector_from_file(file_path):
    # Read the file and extract data
    with open(file_path, 'r') as file:
        lines = file.readlines()
    # Remove the first column headers
    # rows = [line.strip().split('\t')[1:] for line in lines[1:]]
    rows = [line.strip().split('\t')[1:] for line in lines]
    rhs_vector = [float(row[0]) for row in rows]
    return rhs_vector


def check_already_computed(config):
    if os.path.exists(config.summary_filename):
        csv.field_size_limit(sys.maxsize)
        with open(config.summary_filename, 'r') as fsummary:
            summary = csv.DictReader(fsummary, delimiter=';')
            for row in summary:
                if row["instance"] == config.data_name and row["problem"] == config.problem_name and row[
                    "solver_name"] == config.solver_name and row["front_strategy"] == config.front_strategy and row[
                    "solver_search_strategy"] == config.solver_search_strategy and row["fzn_optimisation_level"] == str(
                    config.fzn_optimisation_level) and row["cores"] == str(config.cores) and row[
                    "solver_timeout_sec"] == str(config.solver_timeout_sec):
                    print(f"Skipping {config.uid()} because it is already in {config.summary_filename}")
                    sys.exit(0)


def build_solver(model, instance, config, statistics):
    osolve = build_osolver(model, instance, config, statistics)
    front_generator_strategy = set_front_strategy(config, osolve)
    osolve_mo = build_MO(instance, statistics, front_generator_strategy, osolve, config)
    return osolve_mo, osolve_mo.pareto_front


def build_model(instance, config):
    if instance.is_minizinc:
        return MinizincPseudoModel()
    problem = instance.problem_name
    if not instance.is_minizinc:
        return get_model_by_problem_and_solver_name_(problem, config.solver_name, instance)
    else:
        print(
            "Error. You're trying to build a model from a Minizinc instance. Minizinc instances already have the model")
        sys.exit(1)


def get_model_by_problem_and_solver_name_(problem_name, solver_name, instance):
    if problem_name == constants.Problem.SATELLITE_IMAGE_SELECTION_PROBLEM.value:
        if solver_name == "gurobi":
            return SatelliteImageMosaicSelectionGurobiModel(instance)
        elif solver_name == "ortools-py":
            return SatelliteImageMosaicSelectionOrtoolsCPModel(instance)
    elif problem_name == constants.Problem.MULTI_OBJECTIVE_KNAPSACK_PROBLEM.value:
        if solver_name == "gurobi":
            return MultiobjectiveKnapsackGurobiModel(instance)
        elif solver_name == "ortools-py":
            return MultiobjectiveKnapsackOrtoolsCPModel(instance)
    elif problem_name == constants.Problem.MULTI_OBJECTIVE_N_QUEENS_PROBLEM.value:
        if solver_name == "gurobi":
            return NQueensGurobiModel(instance)


def build_osolver(model, instance, config, statistics):
    free_search = config.solver_search_strategy == "free_search"
    if instance.is_minizinc:
        # todo maybe change the name to indicate that this is using MiniZinc
        # return OSolveCP(instance, statistics, config.threads, free_search,
        #                 config.fzn_optimisation_level)
        solver = MinizincSolver(model, instance, statistics, config.threads, free_search, config.fzn_optimisation_level)
        model.set_solver(solver)
        return solver
    else:
        if config.solver_name == "gurobi":
            solver = GurobiSolver(model, statistics, config.threads, free_search)
            if config.bench_mode:
                # the Gurobi log of every single solve would end up in the bench JSON (MBs for a small instance)
                model.solver_model.Params.OutputFlag = 0
            return solver
        elif config.solver_name == "ortools-py":
            return OrtoolsCPSolver(model, statistics, config.threads, free_search)
        else:
            return GurobiSolver(model, statistics, config.threads, free_search)


def build_timer(config):
    if config.bench_mode:
        # the whole search counts against the timeout, not only the time inside the solver (with fast solvers the
        # Python work between solver calls adds up over thousands of calls)
        return WallClockTimer(config.solver_timeout_sec)
    return Timer(config.solver_timeout_sec)


def set_front_strategy(config, solver):
    if config.front_strategy == "saugmecon":
        return Saugmecon(solver, build_timer(config))
    elif config.front_strategy == "gavanelli":
        return Gavanelli(solver, build_timer(config))
    elif config.front_strategy == "gavanelli-opt":
        return Gavanelli(solver, build_timer(config), optimize=True)
    elif config.front_strategy == "augmecon-coverage":
        return CoverageGridPoint(solver, build_timer(config))
    else:
        return Saugmecon(solver, build_timer(config))


def build_MO(instance, statistics, front_generator, osolve, config):
    # in bench mode the front is not printed after every solution (it would end up in the bench JSON)
    return MOWithFrontGenerator(instance, statistics, front_generator, verbose=not config.bench_mode,
                                 compute_hypervolume_per_solution=config.compute_hypervolume_per_solution)
    # MOCP is used to compute the pareto front with Gavanelli and Minizinc, is not used for the other solvers. It is
    # a bit faster than the current implementation of MOWithFrontGenerator when the solver is accessed through Minizinc
    if instance.is_minizinc:
        return MOCP(instance, statistics, osolve)
    else:
        return MOWithFrontGenerator(instance, statistics, front_generator)


def csv_header(config):
    statistics = {}
    config.init_statistics(statistics)
    init_top_level_statistics(statistics)
    init_solution_details_statistics(statistics)
    return list(statistics.keys())


def create_summary_file(config):
    """We create the CSV summary file if it does not exist yet.
       The header of the summary file is the list of all the statistics the combinators can collect, even if the current solving algorithm do not use all of them.
       This is to be able to compare the statistics of different algorithms.
    """
    if not os.path.exists(config.summary_filename):
        with open(config.summary_filename, "w") as summary:
            writer = csv.DictWriter(summary, fieldnames=csv_header(config), delimiter=';')
            writer.writeheader()


def statistics_to_csv(config, statistics):
    stats_keys = csv_header(config)
    csv_entry = ""
    for k in stats_keys:
        if k in statistics:
            csv_entry += str(statistics[k])
        csv_entry += ";"
    return csv_entry[:-1] + "\n"


def write_statistics(config, statistics):
    try:
        lock = FileLock(config.summary_filename + ".lock", timeout=10)
        with lock:
            create_summary_file(config)
            with open(config.summary_filename, "a") as summary:
                summary.write(statistics_to_csv(config, statistics))
    except Timeout:
        print("Could not acquire lock on summary file. Statistics will be printed on standard output instead.")
        print(statistics_to_csv(config, statistics))


def get_solver_version(config):
    """Version of the solver library that is actually running, e.g. "12.0.1" for Gurobi."""
    if config.solver_name == "gurobi":
        import gurobipy as gp
        return ".".join(str(part) for part in gp.gurobi.version())
    return "unknown"


def print_bench_json_protocol(config, statistics, pareto_front):
    """Print this run's result as the JSON-lines protocol that bench's dump.py/postprocess.py expect from the
    Choco jar, so a Gurobi run can be post-processed into the same campaign CSV as the Choco runs.
    Only what postprocess.py actually reads is included: pareto_front, reference_point, exhaustive and the
    overall solving time. Fields that are Choco-specific (fails, backtracks, nodes, restarts, ...) are simply
    left out, and postprocess.py already leaves those columns blank for a non-Choco solver."""
    reference_point = None
    pareto_front_points = []
    if pareto_front.solutions:
        reference_point = list(pareto_front.solutions[0]["ref_point"])
        pareto_front_points = [list(pareto_front.solutions[f]["objs"]) for f in pareto_front.front]
    # every feasible solution found, in the order found (the infeasible steps of the front generator are None)
    all_solutions = [list(solution["objs"]) for solution in pareto_front.solutions if solution is not None]

    # Plain text line: postprocess.py scans stdout for this to fill the "search_strategy" column.
    print(f"solverSearchStrategy: {config.solver_search_strategy}")

    print(json.dumps({
        "type": "statistics",
        "statistics": {
            "time(s)": statistics["time_total_sec"],
            "sum_solutions_resolution_time(s)": statistics["time_solver_sec"],
            "sum_number_solutions": statistics["number_of_solutions"],
            # Gurobi branch-and-bound nodes summed over all the solver calls (Choco's "Nodes" column, not equivalent
            # one to one). Gurobi has no fails/backtracks/restarts, those columns stay empty.
            "sum_solutions_nodes": int(statistics["total_nodes"]),
            # real version of the solver, it replaces the VERSION that dump.py writes from the launcher script
            "solver_version": get_solver_version(config),
        }
    }))
    print(json.dumps({
        "type": "solutions-details",
        "solutions-details": {
            "pareto_front": pareto_front_points,
            "all_solutions": all_solutions,
            "reference_point": reference_point,
            "exhaustive": statistics["exhaustive"],
            # postprocess.py indexes solver_messages[-1] whenever exhaustive is truthy, so this must be a
            # non-empty list; the text itself is only meaningful for Choco's own parsing, which is skipped
            # for any solver whose name doesn't contain "choco".
            "solver_messages": ["Search completed exhaustively." if statistics["exhaustive"]
                                 else "Incomplete search due to timeout."],
        }
    }))


if __name__ == "__main__":
    main()
