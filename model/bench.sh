cd mo/
cp_strategy="free_search"
cp_timeout_sec=120
solver="gecode"
summary="../summary.csv"

for f in ../data_sets/*.dzn;
do
  if [ -f $f ]
  then
    data_name=$(basename -- "$f" .dzn)
    python3 main.py --model_mzn ../mosaic_cloud2.mzn --objectives_dzn ../objectives.dzn --dzn_dir ../data_sets --solver_name gecode --cp_timeout_sec $cp_timeout_sec --summary ../summary.csv --cp_strategy $cp_strategy --fzn_optimisation_level 1 $data_name
  fi
done
