#!/bin/bash -eu

module purge
module load spark/2.0.1
module load nse/scorePlacement

SLURM_ACCOUNT=proj59 bbp-spark-submit calc_bin_scores.py \
	-m ../tests/data/extNeuronDB.dat \
	-a ../tests/data/ \
	-r ../tests/data/rules.xml \
	-o /dev/stdout
