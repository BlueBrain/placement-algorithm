from __future__ import print_function

import os
import argparse
import numpy as np

from functools import partial


SCORE_CMD = "scorePlacement --annotations {annotations} --rules {rules} --layers {layers}"


def parse_morphdb(elem):
    morph, layer, mtype, etype, _ = elem.split(None, 4)
    return ((morph, mtype), (layer, mtype, etype))


def parse_positions(elem):
    id_, layer, mtype, etype, y, layer_profile = elem.split(None, 5)
    return ((layer, mtype, etype), (id_, y, layer_profile))


def parse_index(elem):
    gid, id_ = elem.split()
    return (id_, int(gid))


def morph_candidates(elem, positions):
    (morph, mtype), key = elem
    return [((morph, mtype), p) for p in positions.get(key, [])]


def format_candidate(elem):
    (morph, mtype), (id_, y, layer_profile) = elem
    return " ".join([morph, mtype, id_, y, layer_profile])


def parse_score(elem):
    morph, id_, score = elem.split()
    return (id_, (morph, float(score)))


def pick_morph(elem, alpha=1.0, index=None, seed=None):
    key, values = elem
    if index is None:
        ids = [key]
    else:
        ids = index[key]

    morph, score = zip(*values)
    morph, score = np.array(morph), np.array(score)

    score = score ** alpha

    score_sum = np.sum(score)
    if score_sum > 0:
        if seed is not None:
            np.random.seed(hash((key, seed)) % (2 ** 32))
            # Sort by morphology name to ensure reproducible random choice
            morph_idx = np.argsort(morph)
            morph, score = morph[morph_idx], score[morph_idx]
        prob = score.astype(float) / score_sum
        chosen = np.random.choice(np.arange(len(morph)), size=len(ids), replace=True, p=prob)
        return [
            (_id, (morph[k], score[k])) for _id, k in zip(ids, chosen)
        ]
    else:
        return [(_id, ("N/A", 0.0)) for _id in ids]


def main(
    morphdb_path, annotations_dir, rules_path, positions_path, index_path,
    layers, profile, alpha,
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
        pick_func = partial(pick_morph, alpha=alpha, index=index, seed=seed)
        result = scores.flatMap(pick_func).sortByKey().collect()
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
        "--alpha",
        type=float,
        default=1.0,
        help="Use `score ** alpha` as morphology choice probability (default: %(default)s)"
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
        args.layers, args.profile, args.alpha,
        seed=args.seed, ntasks=args.ntasks
    )
    with open(args.output, 'w') as f:
        for (id_, (morph, score)) in result:
            print(id_, morph, "%.3f" % score, sep="\t", file=f)
