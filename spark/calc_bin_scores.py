import os
import argparse
import math
import numpy as np

from functools import partial


SCORE_CMD = "scorePlacement --annotations {annotations} --rules {rules} --layers {layers}"


def parse_morphdb(elem):
    morph, layer, other = elem.split(None, 2)
    return (morph, layer), other


def drop_value(elem):
    k, _ = elem
    return k


def get_layer_bins(y0, y1, binsize):
    bin_count = math.ceil((y1 - y0) / binsize) + 1
    borders = np.linspace(y0, y1, bin_count)
    return (borders[:-1] + borders[1:]) / 2


def morph_candidates(elem, layer_profile, binsize):
    morph, layer = elem
    y0, y1 = layer_profile[layer]
    return [
        (morph, ("%s:%d" % (layer, k), y, layer_profile))
        for k, y in enumerate(get_layer_bins(y0, y1, binsize))
    ]


def format_candidate(elem, layer_names):
    morph, (id_, y, layer_profile) = elem
    layer_values = " ".join(["%.3f %.3f" % layer_profile[layer] for layer in layer_names])
    return "%s %s %.3f %s" % (morph, id_, y, layer_values)


def parse_score(elem):
    morph, id_, score = elem.split()
    layer, bin_id = id_.split(":")
    return (morph, layer), (int(bin_id), float(score))


def format_result(elem):
    (morph, layer), (other, scores) = elem
    scores = [v[1] for v in sorted(scores)]
    return " ".join([morph, layer, other] + ["%.3f" % x for x in scores])


def main(morphdb_path, layer_profile, binsize, annotations, rules):
    from pyspark import SparkContext

    layer_names = sorted(layer_profile)

    score_cmd = SCORE_CMD.format(
        annotations=annotations,
        rules=rules,
        layers=",".join(layer_names)
    )

    sc = SparkContext()
    morphdb = sc.textFile(morphdb_path).map(parse_morphdb)

    scores = (morphdb
        .map(drop_value)
        .distinct()
        .flatMap(partial(morph_candidates, layer_profile=layer_profile, binsize=binsize))
        .repartitionAndSortWithinPartitions(100)
        .map(partial(format_candidate, layer_names=layer_names))
        .pipe(score_cmd, env=os.environ)
        .map(parse_score)
        .groupByKey()
    )
    result = morphdb.join(scores).map(format_result)

    print "\n".join(map(str, result.collect()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate placement for constant layer depth profile.")
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
        "-b", "--bin-size",
        default=10,
        type=int,
        help="Bin size (default=%(default)s)"
    )
    args = parser.parse_args()

    layer_profile = {
        '1': (1916.807, 2081.756),
        '2': (1767.931, 1916.807),
        '3': (1415.006, 1767.931),
        '4': (1225.434, 1415.006),
        '5': ( 700.378, 1225.434),
        '6': (       0,  700.378),
    }

    main(args.morphdb, layer_profile, args.bin_size, args.annotations, args.rules)
