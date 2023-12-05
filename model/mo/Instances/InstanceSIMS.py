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