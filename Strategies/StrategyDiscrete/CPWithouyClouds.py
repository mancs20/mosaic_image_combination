from Strategies.StrategyDiscrete.StrategyDiscrete import StrategyDiscrete


class CPWithoutClouds(StrategyDiscrete):
    path = ""
    name = "Constraint_Programming_Discrete_Without_Clouds"
    number_of_runs = 1
    def run_strategy(self):
        super().discretize()
        self.call_cp(self.sets_images, self.universe)
    def call_cp(self):
        result = 1;