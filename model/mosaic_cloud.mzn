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

constraint forall(u in UNIVERSE)(
  exists(i in IMAGES)(taken[i] /\ u in images[i]));

array[IMAGES] of var float: sums;

constraint
  forall(i in IMAGES)(
    sums[i] = taken[i] * sum(u in images[i] where u in clouds[i])(
      areas[u] * (
        forall(j in IMAGES where i != j /\ u in images[j] /\ not (u in clouds[j]))(
          not taken[j]
        )
      )
    )
  );
  
constraint sum(i in IMAGES)(sums[i]) <= max_cloud_area;

var float: obj = sum(i in IMAGES)(costs[i] * taken[i]);
solve minimize obj;
% output ["taken = \(taken);\n"];
