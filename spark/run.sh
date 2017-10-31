#!/bin/bash -eu

module purge
module load spark/2.2.0

export PATH=../cpp:$PATH  # find `scorePlacement` binary

spark-submit calc_all_scores.py \
	-p ../tests/data/positions.tsv \
	-m ../tests/data/extNeuronDB.dat \
	-a ../tests/data/ \
	-r ../tests/data/rules.xml \
	-l 6,5,4,3,2,1 \
	--profile 700,525,190,353,149,165 \
	-o /dev/stdout
