from Strategies.StrategyDiscrete.StrategyDiscrete import StrategyDiscrete


class CPWithoutClouds(StrategyDiscrete):
    path = ""
    name = "Constraint_Programming_Discrete_Without_Clouds"
    number_of_runs = 1
    def run_strategy(self):
        super().discretize()
        self.export_set_images_universe_to_dzn(self.sets_images, self.universe)
        # self.call_cp_solver(self.sets_images, self.universe)

    def export_set_images_universe_to_dzn(self, sets_images, universe):
        with open(self.path + "/CPWithoutClouds.dzn", "w") as f:
            f.write("images = " + str(len(sets_images)) + ";\n")
            f.write("universe = " + str(universe) + ";\n")
            f.write("sets = [")
            for i in range(len(sets_images)):
                f.write("{")
                for j in range(len(sets_images[i].list_of_regions)):
                    f.write(str(sets_images[i].list_of_regions[j]))
                    if j < len(sets_images[i].list_of_regions) - 1:
                        f.write(", ")
                f.write("}")
                if i < len(sets_images) - 1:
                    f.write(", ")
            f.write("];\n")
            f.write("costs = [")
            for i in range(len(sets_images)):
                f.write(str(sets_images[i].weight))
                if i < len(sets_images) - 1:
                    f.write(", ")
            f.write("];\n")
    def call_cp_solver(self):
        result = 1;