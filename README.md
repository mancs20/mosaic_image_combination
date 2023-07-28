## Package dependencies
You need the following packages to be installed:

* [minizinc](https://www.minizinc.org/)
  * `pip install minizinc[dzn] dataclasses-json contextily`
* [gurobi](https://www.gurobi.com/)
  * `pip install gurobipy`
* [Up42 SDK](https://sdk.up42.com/installation/) with plotting functionalities
  * `pip install "up42-py[viz]"`
* [dataclasses-json](https://pypi.org/project/dataclasses-json/)
  * `pip install dataclasses-json`

## Usage

### Download data from UP42
First you need to define the AOI and place it in the aois folder, there is already some examples of AOI in the folder. The AOI files are in GeoJSON format.

To download data from UP42 you need to have an account and an API key. You can find the API key in your profile settings. You can set the API key in the file `config.json` like below:
```json
{
    "project_id": "your_project_id",
    "project_api_key": "your_project_api_key"
}
```
In ProjectDataClasses you can change the search parameters in the dataclass SearchParameters. The search parameters are the following:
* `start_date`: The start date of the search. It is a string in the following format: `YYYY-MM-DD`. Example: `2021-01-01` 
* `end_date`: The end date of the search. It is a string in the following format: `YYYY-MM-DD`. Example: `2023-01-01`
* `collection`: Array of image collection to search for. The default value is `[phr, spot, pneo]`. `phr` is Pleiades High Resolution, `spot` is SPOT 6/7 and `pneo` is Pleiades Neo.
* `cloud_cover`: The maximum cloud cover of the images. It is a float between 0 and 100.
* `limit`: The maximum number of images to return. It is an integer between 1 and 500.

The downloaded data will be stored in the folder `results/aoi_name/search_range_date/number_of_images`, example `results/paris/2021-01-01-2023-01-01/500`.
Inside the folder there will be the following files:

### Run the experiments



### Convert float values in the data set to integers





