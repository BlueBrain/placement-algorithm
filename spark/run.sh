#!/bin/bash -eu

module purge
module load spark/2.0.1
module load nse/scoreCandidates

spark-submit calc_bin_scores.py $@