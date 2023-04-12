include "globals.mzn";

int: images;
int: universe;

set of int: IMAGES = 1..images;
set of int: UNIVERSE = 1..universe;

array[IMAGES] of set of int: sets;
array[IMAGES] of float: costs;

constraint forall(u in UNIVERSE)(
  exists(i in IMAGES)(taken[i] /\ u in sets[i]));

array[IMAGES] of var bool: taken;

solve minimize sum(i in IMAGES)(costs[i] * taken[i]);

output ["taken = \(taken);\n"];
