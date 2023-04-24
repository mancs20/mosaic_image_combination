class Region:
   def __init__(self):
        self.id = 0
        self.list_of_belonging_image_set = []
        self.penalized: bool = False
        self.area: float = 0.0