import sys
import os
from pathlib import Path

p = Path(__file__).parents[3]

# Get the root directory
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
# Add the root directory to sys.path
sys.path.append(root_dir)
# Import the module from the root directory
import constants

from model.mo.Instances.InstanceGeneric import InstanceGeneric


class InstanceSIMS(InstanceGeneric):
  # def __init__(self, images, costs, areas, clouds, max_cloud_area, resolution, incidence_angle):
  def __init__(self, minizinc_instance):
    super().__init__(is_minizinc=False, problem_name=constants.Problem.SATELLITE_IMAGE_SELECTION_PROBLEM.value)
    self.images, self.clouds = self.correct_starting_indexes(minizinc_instance["images"], minizinc_instance["clouds"])
    self.costs = minizinc_instance["costs"]
    self.areas = minizinc_instance["areas"]
    # The data has a different set of fields per variant (cost+clouds, cost+clouds+angle, ...):
    # a field that is not in the data is None, and its objective is not part of the problem.
    self.max_cloud_area = self.get_optional_field(minizinc_instance, "max_cloud_area")
    self.resolution = self.get_optional_field(minizinc_instance, "resolution")
    self.incidence_angle = self.get_optional_field(minizinc_instance, "incidence_angle")
    self.active_objectives = ["cost", "clouds"]
    if self.resolution is not None:
      self.active_objectives.append("resolution")
    if self.incidence_angle is not None:
      self.active_objectives.append("incidence_angle")
    self.cloud_covered_by_image, self.clouds_id_area = self.get_clouds_covered_by_image()

  @staticmethod
  def get_optional_field(minizinc_instance, name):
    try:
      return minizinc_instance[name]
    except KeyError:
      return None

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