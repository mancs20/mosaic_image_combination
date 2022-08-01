from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class SearchParameters:
    aoi = None
    start_date: str = "2020-01-01"
    end_date: str = "2022-07-01"
    collections = ["phr"]
    max_cloudcover: float = 50
    limit: int = 20


@dataclass
class OptimizationResult:
    number_of_images = 0
    total_area_of_images = 0
    overlapping_area_inside_aoi = 0
    total_cost_of_images = 0
