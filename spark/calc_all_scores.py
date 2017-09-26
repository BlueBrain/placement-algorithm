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


def parse_index(elem):
    gid, id_ = elem.split()
    return (id_, int(gid))


def morph_candidates(elem, positions):
    morph, key = elem
    return [(morph, p) for p in positions.get(key, [])]


def format_candidate(elem):
    morph, (id_, y, layer_profile) = elem
    return " ".join([morph, id_, y, layer_profile])


def parse_score(elem):
    morph, id_, score = elem.split()
    return (id_, (morph, float(score)))


def pick_morph(elem, index=None, seed=None):
    key, values = elem
    if index is None:
        ids = [key]
    else:
        ids = index[key]

    morph, score = zip(*sorted(values))

    score_sum = np.sum(score)
    if score_sum > 0:
        if seed is not None:
            np.random.seed(hash((key, seed)) % (2 ** 32))
        chosen = np.random.choice(np.arange(len(morph)), size=len(ids), replace=True, p=score / score_sum)
        return [
            (_id, (morph[k], score[k])) for _id, k in zip(ids, chosen)
        ]
    else:
        return [(_id, ("N/A", 0.0)) for _id in ids]


def main(
    morphdb_path, annotations_dir, rules_path, positions_path, index_path,
    layers, profile,
    seed=None, ntasks=1000
):
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
        positions = sc.broadcast(sc.textFile(positions_path)
            .map(parse_positions)
            .groupByKey()
            .mapValues(list)
            .collectAsMap()
        ).value
        if index_path is None:
            index = None
        else:
            index = sc.broadcast(sc.textFile(index_path)
                .map(parse_index)
                .groupByKey()
                .mapValues(list)
                .collectAsMap()
            ).value
        scores = (morphdb
            .distinct()
            .repartitionAndSortWithinPartitions(ntasks)
            .flatMap(partial(morph_candidates, positions=positions))
            .map(format_candidate)
            .pipe(score_cmd, env=os.environ)
            .map(parse_score)
            .groupByKey()
        )
        result = scores.flatMap(partial(pick_morph, index=index, seed=seed)).sortByKey().collect()
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
        "--profile",
        default=None,
        help="Layer thickness ratio to use for 'short' candidate form (comma-separated)"
    )
    parser.add_argument(
        "-p", "--positions",
        required=True,
        help="Path to .tsv with positions to consider"
    )
    parser.add_argument(
        "-i", "--index",
        default=None,
        help="Path to .tsv with positions reverse index (optional)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random number generator seed"
    )
    parser.add_argument(
        "--ntasks",
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

    result = main(
        args.morphdb, args.annotations, args.rules, args.positions, args.index,
        args.layers, args.profile,
        seed=args.seed, ntasks=args.ntasks
    )
    with open(args.output, 'w') as f:
        for (id_, (morph, score)) in result:
            print(id_, morph, "%.3f" % score, sep="\t", file=f)
