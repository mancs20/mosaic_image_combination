include "globals.mzn";

int: num_images;
int: universe;
float: max_cloud_area;

set of int: IMAGES = 1..num_images;
set of int: UNIVERSE = 1..universe;

array[IMAGES] of set of int: images;
array[IMAGES] of set of int: clouds;
array[IMAGES] of float: costs;
array[UNIVERSE] of float: areas;

array[IMAGES] of var bool: taken;

% Which images have a universe `u` without cloud?
% That is, uclear[u] = {i1, i2, ..} means that the images numbered i1, i2, ... contains `u` without clouds.
array[UNIVERSE] of set of int: uclear = [{ i | i in IMAGES where not (u in clouds[i]) } | u in UNIVERSE];

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

var float: cloudy_area = sum(u in UNIVERSE)(cloudy[u] * areas[u]);
constraint cloudy_area <= max_cloud_area;

var float: total_cost = sum(i in IMAGES)(costs[i] * taken[i]);

% These variables are for the search strategy, reflecting the greedy strategy for set cover.

% array[UNIVERSE] of set of int: images_inv = [ { i | i in IMAGES where u in images[i] } | u in UNIVERSE ];

% % utaken[u] is true if the universe is already taken.
% array[UNIVERSE] of var bool: utaken;
% constraint forall(u in UNIVERSE)(utaken[u] = (sum(i in images_inv[u])(taken[i]) > 0));

% % This variable is only there for the search strategy (based on the greedy algorithm).
% % At some points in the search tree, if covered[i] = [lb..ub], it means that `lb` pieces of the image `i` are already covered.
% % When an image is covered, we have covered[i] = ub, since ub represents the number of pieces in that image.
% % When we reach a solution, we have covered[i] = ub for all image i.
% array[IMAGES] of var int: covered;
% constraint forall(i in IMAGES)(covered[i] = sum(u in images[i])(utaken[u]));

% % Channeling between taken and covered, to make sure searching on covered also assign the variable in taken.
% constraint forall(i in IMAGES)(taken[i] <-> covered[i] = card(images[i]));

solve
%   ::int_search(covered, anti_first_fail, indomain_max)
minimize total_cost;
