from __future__ import print_function

import os
import argparse
import numpy as np

from functools import partial


SCORE_CMD = "scorePlacement --annotations {annotations} --rules {rules} --layers {layers}"


def parse_morphdb(elem):
    morph, layer, mtype, etype, _ = elem.split(None, 4)
    return (morph, (layer, mtype, etype))


def parse_positions(elem):
    id_, layer, mtype, etype, y, layer_profile = elem.split(None, 5)
    return ((layer, mtype, etype), (id_, y, layer_profile))


def morph_candidates(elem, positions):
    morph, key = elem
    return [(morph, p) for p in positions.get(key, [])]


def format_candidate(elem):
    morph, (id_, y, layer_profile) = elem
    return " ".join([morph, id_, y, layer_profile])


def parse_score(elem):
    morph, id_, score = elem.split()
    return (id_, (morph, float(score)))


def pick_morph(elem, seed=None):
    key, values = elem

    if ";" in key:
        id_, count = key.split(";", 1)
        count = int(count)
        format_id = lambda k: "%s;%d" % (id_, k)
    else:
        id_, count = key, 1
        format_id = lambda _: id_

    morph, score = zip(*sorted(values))

    score_sum = np.sum(score)
    if score_sum > 0:
        if seed is not None:
            np.random.seed(hash((key, seed)) % (2 ** 32))
        chosen = np.random.choice(np.arange(len(morph)), size=count, replace=True, p=score / score_sum)
        return [
            (format_id(k), (morph[j], score[j])) for k, j in enumerate(chosen)
        ]
    else:
        return [
            (format_id(k), ("N/A", 0.0)) for k in xrange(count)
        ]


def main(morphdb_path, annotations_dir, rules_path, positions_path, layers, profile, seed=None, ntasks=1000):
    from pyspark import SparkContext

    score_cmd = SCORE_CMD.format(
        annotations=annotations_dir,
        rules=rules_path,
        layers=layers
    )

    if profile is not None:
        score_cmd+= " --profile " + profile

    sc = SparkContext()

    try:
        morphdb = sc.textFile(morphdb_path).map(parse_morphdb)
        positions = sc.textFile(positions_path).map(parse_positions)
        positions_map = sc.broadcast(positions
            .groupByKey()
            .mapValues(list)
            .collectAsMap()
        )
        scores = (morphdb
            .distinct()
            .repartitionAndSortWithinPartitions(ntasks)
            .flatMap(partial(morph_candidates, positions=positions_map.value))
            .map(format_candidate)
            .pipe(score_cmd, env=os.environ)
            .map(parse_score)
            .groupByKey()
        )
        result = scores.flatMap(partial(pick_morph, seed=seed)).sortByKey().collect()
    finally:
        sc.stop()

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate placement for varying layer depth profile.")
    parser.add_argument(
        "-m", "--morphdb",
        required=True,
        help="Path to MorphDB file"
    )
    parser.add_argument(
        "-a", "--annotations",
        required=True,
        help="Path to annotations folder"
    )
    parser.add_argument(
        "-r", "--rules",
        required=True,
        help="Path to placement rules file"
    )
    parser.add_argument(
        "-l", "--layers",
        required=True,
        help="Layer names as they appear in layer profile (comma-separated)"
    )
    parser.add_argument(
        "-p", "--profile",
        default=None,
        help="Layer thickness ratio to use for 'short' candidate form (comma-separated)"
    )
    parser.add_argument(
        "-i", "--positions",
        required=True,
        help="Path to CSV with positions to consider"
    )
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=None,
        help="Random number generator seed"
    )
    parser.add_argument(
        "-t", "--ntasks",
        type=int,
        default=100,
        help="Number of Spark tasks to use for scoring (default: %(default)s)"
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Path to output file"
    )
    args = parser.parse_args()

    result = main(args.morphdb, args.annotations, args.rules, args.positions, args.layers, args.profile, seed=args.seed, ntasks=args.ntasks)
    with open(args.output, 'w') as f:
        for (id_, (morph, score)) in result:
            print(id_, morph, "%.3f" % score, file=f)
