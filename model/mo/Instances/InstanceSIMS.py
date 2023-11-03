import constants
from model.mo.Instances.InstanceGeneric import InstanceGeneric


class InstanceSIMS(InstanceGeneric):
  # def __init__(self, images, costs, areas, clouds, max_cloud_area, resolution, incidence_angle):
  def __init__(self, minizinc_instance):
    super().__init__(is_minizinc=False, problem_name=constants.Problem.SATELLITE_IMAGE_SELECTION_PROBLEM.value)
    self.images, self.clouds = self.correct_starting_indexes(minizinc_instance["images"], minizinc_instance["clouds"])
    self.costs = minizinc_instance["costs"]
    self.areas = minizinc_instance["areas"]
    self.max_cloud_area = minizinc_instance["max_cloud_area"]
    self.resolution = minizinc_instance["resolution"]
    self.incidence_angle = minizinc_instance["incidence_angle"]
    self.cloud_covered_by_image, self.clouds_id_area = self.get_clouds_covered_by_image()

  def get_clouds_covered_by_image(self):
    cloud_covered_by_image = {}
    clouds_id_area = {}
    for i in range(len(self.clouds)):
      image_cloud_set = self.clouds[i]
      for cloud_id in image_cloud_set:
        if cloud_id not in clouds_id_area:
          clouds_id_area[cloud_id] = self.areas[cloud_id]
        for j in range(len(self.images)):
          if i != j:
            if cloud_id in self.images[j] and cloud_id not in self.clouds[j]:  # the area of the cloud is covered by image j, and it is not cloudy in j
              if j in cloud_covered_by_image:
                cloud_covered_by_image[j].add(cloud_id)
              else:
                cloud_covered_by_image[j] = {cloud_id}
    return cloud_covered_by_image, clouds_id_area

  @staticmethod
  def correct_starting_indexes(images, clouds):
      for i in range(len(images)):
          images[i] = {x - 1 for x in images[i]}
      for i in range(len(clouds)):
          clouds[i] = {x - 1 for x in clouds[i]}
      for i in range(len(clouds)):
          if len(clouds[i]) == 0:
              clouds[i] = {}
      return images, clouds

  def get_ref_points_for_hypervolume(self):
      ref_points = [sum(self.costs) + 1, sum(self.areas) + 1,
                    self.get_resolution_nadir_for_ref_point() + 1, 900]
      return ref_points

  def get_resolution_nadir_for_ref_point(self):
      resolution_parts_max = {}
      for idx, image in enumerate(self.images):
          for u in image:
              if u not in resolution_parts_max:
                  resolution_parts_max[u] = self.resolution[idx]
              else:
                  if resolution_parts_max[u] < self.resolution[idx]:
                      resolution_parts_max[u] = self.resolution[idx]
      return sum(resolution_parts_max.values())

  def get_nadir_bound_estimation(self):
      nadir_objectives = [sum(self.costs), sum(self.areas), self.get_resolution_nadir_for_ref_point(), max(self.incidence_angle)]
      return nadir_objectives

  def assert_solution(self, solution, selected_images):
      self.assert_cost(selected_images, solution[0])
      self.assert_cloud_covered(selected_images, solution[1])
      self.assert_resolution(selected_images, solution[2])
      self.assert_incidence_angle(selected_images, solution[3])

  def assert_cost(self, selected_images, cost):
      total_cost = 0
      for image in selected_images:
          total_cost += self.costs[image]
      assert total_cost == cost

  def assert_cloud_covered(self, selected_images, cloud_uncovered):
      total_cloud_covered = 0
      cloud_covered = set()
      for image in selected_images:
          if image in self.cloud_covered_by_image:
              for cloud in self.cloud_covered_by_image[image]:
                  if cloud not in cloud_covered:
                      cloud_covered.add(cloud)
                      total_cloud_covered += self.clouds_id_area[cloud]
      total_area_clouds = int(sum(self.clouds_id_area.values()))
      assert total_area_clouds - total_cloud_covered == cloud_uncovered

  def assert_resolution(self, selected_images, resolution):
      calculated_total_resolution = 0
      for element in range(len(self.areas)):
          element_resolution = max(self.resolution)
          for image in selected_images:
              if element in self.images[image]:
                  if self.resolution[image] < element_resolution:
                      element_resolution = self.resolution[image]
          calculated_total_resolution += element_resolution
      assert calculated_total_resolution == resolution

  def assert_incidence_angle(self, selected_images, incidence_angle):
      max_incidence_angle = 0
      for image in selected_images:
          if self.incidence_angle[image] > max_incidence_angle:
              max_incidence_angle = self.incidence_angle[image]
      assert max_incidence_angle == incidence_angle


