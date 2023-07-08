include "globals.mzn";

int: num_images;
int: universe;
int: max_cloud_area;

set of int: IMAGES = 1..num_images;
set of int: UNIVERSE = 1..universe;

array[IMAGES] of set of int: images;
array[IMAGES] of set of int: clouds;
array[IMAGES] of int: costs;
array[UNIVERSE] of int: areas;
array[IMAGES] of int: resolution;
array[IMAGES] of int: incidence_angle;

array[IMAGES] of var bool: taken;

% Which images have a universe `u` without cloud?
% That is, uclear[u] = {i1, i2, ..} means that the images numbered i1, i2, ... contains `u` without clouds.
array[UNIVERSE] of set of int: uclear = [{ i | i in IMAGES where not (u in clouds[i]) /\ u in images[i] } | u in UNIVERSE];

% Set covering constraint.
constraint forall(u in UNIVERSE)(
  exists(i in IMAGES)(taken[i] /\ u in images[i]));

% cloudy[u] is true iff no image containing a version of `u` without clouds is taken.
array[UNIVERSE] of var bool: cloudy;
array[UNIVERSE] of var int: num_clear_images;
constraint forall(u in UNIVERSE)(
  num_clear_images[u] = sum(i in uclear[u])(taken[i])
);
constraint forall(u in UNIVERSE)(cloudy[u] = (num_clear_images[u] == 0));

var int: cloudy_area = sum(u in UNIVERSE)(cloudy[u] * areas[u]);

var int: total_cost = sum(i in IMAGES)(costs[i] * taken[i]);
var int: max_resolution = sum(u in UNIVERSE)(min(i in IMAGES where u in images[i] /\ taken[i])(resolution[i]));
var int: max_incidence = max(i in IMAGES)(taken[i] * incidence_angle[i]);

array[1..4] of var int: objs;
constraint objs[1] = cloudy_area;
constraint objs[2] = total_cost;
constraint objs[3] = max_resolution;
constraint objs[4] = max_incidence;

array[1..4] of var bool: minimize_objs;
array[1..4] of var int: ref_point;

constraint ref_point[1] = sum(u in UNIVERSE)(areas[u]) + 1;
constraint ref_point[2] = sum(i in IMAGES)(costs[i]) + 1;
constraint ref_point[3] = sum(u in UNIVERSE)(max(i in IMAGES where u in images[i])(resolution[i])) + 1;
constraint ref_point[4] = 900;

constraint minimize_objs[1] = true;
constraint minimize_objs[2] = true;
constraint minimize_objs[3] = true;
constraint minimize_objs[4] = true;

% These variables are for the search strategy, reflecting the greedy strategy for set cover.

array[UNIVERSE] of set of int: images_inv = [ { i | i in IMAGES where u in images[i] } | u in UNIVERSE ];

% utaken[u] is true if the universe is already taken.
array[UNIVERSE] of var bool: utaken;
constraint forall(u in UNIVERSE)(utaken[u] = exists(i in images_inv[u])(taken[i]));

% This variable is only there for the search strategy (based on the greedy algorithm).
% At some points in the search tree, if covered[i] = [lb..ub], it means that `lb` pieces of the image `i` are already covered.
% When an image is covered, we have covered[i] = ub, since ub represents the number of pieces in that image.
% When we reach a solution, we have covered[i] = ub for all image i.
array[IMAGES] of var int: covered;
constraint forall(i in IMAGES)(covered[i] = sum(u in images[i])(utaken[u]));

% Redundant constraint
constraint forall(i in IMAGES)(taken[i] -> covered[i] = card(images[i]));

solve
   ::int_search(covered, anti_first_fail, indomain_max)
satisfy;
