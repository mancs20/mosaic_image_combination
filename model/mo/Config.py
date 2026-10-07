import os
import glob
import argparse
import multiprocessing

class Config:
    """Configuration class for the multi-objective constraint programming.
       It parses the commandline arguments and initializes the temporary and result directories."""
    def __init__(self):
        parser = argparse.ArgumentParser(
            prog = 'multi_objective_cp',
            description = 'Multi-objective constraint programming. This program computes a Pareto front of an optimization constraint problem.')
        parser.add_argument('--instance_name', required=True)
        parser.add_argument('--minizinc_data', required=False)
        parser.add_argument('--model_mzn', required=False)
        parser.add_argument('--dzn_dir', required=False)
        parser.add_argument('--problem_name', required=True)
        parser.add_argument('--solver_name', required=True)
        parser.add_argument('--front_strategy', required=True)
        parser.add_argument('--solver_timeout_sec', required=True, type=int)
        parser.add_argument('--summary', required=True)
        parser.add_argument('--cores', type=int)
        parser.add_argument('--solver_search_strategy', required=True)             # Must be "free" or the name of a CP strategy (only for information purposes, the strategy must be described in the model).
        parser.add_argument('--fzn_optimisation_level', required=True, type=int)
        parser.add_argument('--compute_hypervolume_per_solution', type=int, default=1, required=False)
        parser.add_argument('--benchmark_name', type=str, default="default", required=False)
        parser.add_argument('--instance_path', required=False)
        args = parser.parse_args()
        # Bench mode: when --instance_path is given (same 4 fields as the bench CSVs: benchmark_name, problem,
        # instance, instance_path), the model, the data and the kind of data are derived from that path.
        # Without --instance_path nothing changes: --minizinc_data, --model_mzn and --dzn_dir are required.
        self.bench_mode = args.instance_path is not None
        self.data_name = args.instance_name
        if self.bench_mode:
            self.init_data_files_from_bench_instance_path(args.instance_path)
        else:
            if args.minizinc_data is None or args.model_mzn is None or args.dzn_dir is None:
                parser.error("--minizinc_data, --model_mzn and --dzn_dir are required unless --instance_path is given")
            args.dzn_dir = self.clean_dir_name(args.dzn_dir)
            self.minizinc_data = bool(int(args.minizinc_data))
            self.data_sets_folder = args.dzn_dir
            self.input_mzn = args.model_mzn
            self.minizinc_model = os.path.basename(self.input_mzn)[:-4]
            self.input_dzn = args.dzn_dir + "/" + args.problem_name + "/" + self.data_name + ".dzn"
        self.solver_name = args.solver_name
        self.problem_name = args.problem_name
        self.front_strategy = args.front_strategy
        self.solver_timeout_sec = args.solver_timeout_sec
        self.summary_filename = args.summary
        self.solver_search_strategy = args.solver_search_strategy
        self.fzn_optimisation_level = args.fzn_optimisation_level
        self.cores = args.cores
        self.threads = None
        self.compute_hypervolume_per_solution = bool(int(args.compute_hypervolume_per_solution))
        self.benchmark_name = args.benchmark_name
        self.instance_path = args.instance_path

    def init_data_files_from_bench_instance_path(self, instance_path):
        """Derive model and data from the instance path: a .dzn/.fzn path means MiniZinc data
        (the .dzn has the same name and the only .mzn of the folder is the model); any other extension (e.g. the
        .dat of the MOOLibrary knapsacks) is read directly from that file."""
        path = os.path.realpath(instance_path)
        folder, filename = os.path.split(path)
        base, extension = os.path.splitext(filename)
        self.data_sets_folder = folder
        if extension in (".dzn", ".fzn"):
            self.minizinc_data = True
            self.input_dzn = os.path.join(folder, base + ".dzn")
            models = sorted(glob.glob(os.path.join(folder, "*.mzn")))
            if len(models) != 1:
                raise SystemExit(f"Expected exactly one .mzn model in {folder}, found {len(models)}: {models}")
            self.input_mzn = models[0]
            self.minizinc_model = os.path.basename(self.input_mzn)[:-4]
        else:
            self.minizinc_data = False
            self.input_dzn = path
            self.input_mzn = None
            self.minizinc_model = ""

    @staticmethod
    def clean_dir_name(directory):
        """Remove the last '/' if it exists."""
        if directory[-1] == '/':
            directory = directory[:-1]
        return directory

    def init_statistics(self, statistics):
        statistics["instance"] = self.data_name
        statistics["problem"] = self.problem_name
        statistics["solver_name"] = self.solver_name
        statistics["front_strategy"] = self.front_strategy
        statistics["solver_search_strategy"] = self.solver_search_strategy
        statistics["fzn_optimisation_level"] = self.fzn_optimisation_level
        statistics["threads"] = self.threads
        statistics["cores"] = self.cores
        statistics["solver_timeout_sec"] = self.solver_timeout_sec
        statistics["minizinc_model"] = self.minizinc_model

    def uid(self):
        """Unique identifier for this experiment."""
        return self.data_name + "_" + self.problem_name + "_" + self.solver_name + "_" + self.front_strategy + "_" + self.minizinc_model + "_" + self.solver_search_strategy + "_" + str(self.solver_timeout_sec) + "_" + str(self.fzn_optimisation_level) + "_" + str(self.cores)

    def initialize_cores(self, solver, check_solver = True):
        """If the solver supports parallelization, use twice the number of available cores. By default, we assume that it does."""
        if not check_solver:
            print("Check if the solver supports parallelization. By default, we assume that it does.")
        if not check_solver or "-p" in solver.stdFlags:
            if self.cores is None:
                self.cores = multiprocessing.cpu_count()
            self.threads = self.cores # I use the same number of threads as cores to run experiments using only one thread like in Choco, it was for comparison purposes, but it can be changed to use more threads than cores if needed.
        else:
            self.cores = 1
            self.threads = 1
