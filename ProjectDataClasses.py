from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class SearchParameters:
    aoi = None
    start_date: str = "2020-01-01"
    end_date: str = "2022-10-01"
    collections = ["phr"]
    max_cloudcover: float = 100
    limit: int = 30


@dataclass
class OptimizationResult:
    experiment_id: int = 1
    images_id: str = '2-1-3'
    images_id_sorted: str = '1-2-3'
    number_of_images: int = 0
    area_of_images_km2: float = 0.0
    area_of_images_over_aoi: float = 0.0
    overlapping_area_inside_aoi: float = 0.0
    total_cost_of_images: float = 0.0
