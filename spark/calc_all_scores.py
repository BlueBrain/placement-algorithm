from __future__ import print_function

import os
import argparse
import numpy as np


SCORE_CMD = "scorePlacement --annotations {annotations} --rules {rules} --layers {layers}"


def parse_morphdb(elem):
    morph, layer, mtype, etype, _ = elem.split(None, 4)
    return ((layer, mtype, etype), morph)


def parse_positions(elem):
    gid, layer, mtype, etype, y, layer_profile = elem.split(None, 5)
    return ((layer, mtype, etype), (gid, y, layer_profile))


def drop_key(elem):
    _, v = elem
    return v


def format_candidate(elem):
    morph, (gid, y, layer_profile) = elem
    return " ".join([morph, gid, y, layer_profile])


def parse_score(elem):
    morph, gid, score = elem.split()
    return (gid, (morph, float(score)))


def pick_morph(elem):
    morphs, scores = zip(*elem)
    scores = np.array(scores)
    score_sum = np.sum(scores)
    if score_sum > 0:
        result = np.random.choice(morphs, p=scores / score_sum)
    else:
        result = "<none>"
    return result


def main(morphdb_path, annotations_dir, rules_path, positions_path, layers):
    from pyspark import SparkContext

    score_cmd = SCORE_CMD.format(
        annotations=annotations_dir,
        rules=rules_path,
        layers=layers
    )

    sc = SparkContext()

    try:
        morphdb = sc.textFile(morphdb_path).map(parse_morphdb).distinct()
        positions = sc.textFile(positions_path).map(parse_positions)
        scores = (
            morphdb.join(positions)
            .map(drop_key)
            .repartitionAndSortWithinPartitions(1000)
            .map(format_candidate)
            .pipe(score_cmd, env=os.environ)
            .map(parse_score)
            .groupByKey()
        )
        result = scores.mapValues(pick_morph).sortByKey().collect()
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
        "-p", "--positions",
        required=True,
        help="Path to CSV with positions to consider"
    )
    parser.add_argument(
        "-l", "--layers",
        required=True,
        help="Layer names as they appear in layer profile (comma-separated)"
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Path to output file"
    )
    args = parser.parse_args()

    result = main(args.morphdb, args.annotations, args.rules, args.positions, args.layers)
    with open(args.output, 'w') as f:
        for gid, morph in result:
            print(gid, morph, file=f)
