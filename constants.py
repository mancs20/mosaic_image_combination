from enum import Enum

PLANAR_CRS = 3857

# file names
DATA_FILE_NAME_CSV = 'images_data.csv'
DATA_FILE_NAME = 'images_data.geojson'
COVERAGE_IMAGE_NAME = 'coverage.svg'
EXPERIMENT_RESULTS_FILE = 'experiment_results.csv'
EXPERIMENT_RESULTS_GEOJSON = 'experiment_results_'
EXPERIMENT_RESULTS_COVERAGE = 'experiment_result_coverage_'

# folder names
QUICKLOOKS_FOLDER_NAME = 'quicklooks'

# type of clouds
class Clouds(Enum):
    NO_CLOUDS = "No_Clouds"
    ARTIFICIAL_CLOUDS_COVERING_WHOLE_INTERSECTION = "Artificial_Clouds_Covering_Whole_Intersection"
    REAL_CLOUDS = "Real_Clouds"


# Colors for 20 pictures
COLORS_20 = [
    '#d3d3d3',

    # maroon2
    #
    '#7f0000',
    #
    # olive
    #
    '#808000',
    #
    # mediumseagreen
    #
    '#3cb371',
    #
    # darkcyan
    #
    '#008b8b',
    #
    # darkmagenta
    #
    '#8b008b',
    #
    # red
    #
    '#ff0000',
    #
    # darkorange
    #
    '#ff8c00',
    #
    # gold
    #
    '#ffd700',
    #
    # mediumblue
    #
    '#0000cd',
    #
    # springgreen
    #
    '#00ff7f',
    #
    # royalblue
    #
    '#4169e1',
    #
    # darksalmon
    #
    '#e9967a',
    #
    # aqua
    #
    '#00ffff',
    #
    # deepskyblue
    #
    '#00bfff',
    #
    # greenyellow
    #
    '#adff2f',
    #
    # fuchsia
    #
    '#ff00ff',
    #
    # khaki
    #
    '#f0e68c',
    #
    # plum
    #
    '#dda0dd',
    #
    # deeppink
    #
    '#ff1493']

COLORS_30 = [
    # darkslategray
    #
    '#2f4f4f',
    #
    # saddlebrown
    #
    '#8b4513',
    #
    # olive
    #
    '#808000',
    #
    # darkslateblue
    #
    '#483d8b',
    #
    # green
    #
    '#008000',
    #
    # rosybrown
    #
    '#bc8f8f',
    #
    # steelblue
    #
    '#4682b4',
    #
    # darkblue
    #
    '#00008b',
    #
    # darkseagreen
    #
    '#8fbc8f',
    #
    # purple
    #
    '#800080',
    #
    # maroon3
    #
    '#b03060',
    #
    # orangered
    #
    '#ff4500',
    #
    # darkorange
    #
    '#ff8c00',
    #
    # yellow
    #
    '#ffff00',
    #
    # lime
    #
    '#00ff00',
    #
    # blueviolet
    #
    '#8a2be2',
    #
    # springgreen
    #
    '#00ff7f',
    #
    # crimson
    #
    '#dc143c',
    #
    # aqua
    #
    '#00ffff',
    #
    # sandybrown
    #
    '#f4a460',
    #
    # blue
    #
    '#0000ff',
    #
    # greenyellow
    #
    '#adff2f',
    #
    # fuchsia
    #
    '#ff00ff',
    #
    # dodgerblue
    #
    '#1e90ff',
    #
    # plum
    #
    '#dda0dd',
    #
    # lightgreen
    #
    '#90ee90',
    #
    # lightblue
    #
    '#add8e6',
    #
    # deeppink
    #
    '#ff1493',
    #
    # mediumslateblue
    #
    '#7b68ee',
    #
    # moccasin
    #
    '#ffe4b5',
]
