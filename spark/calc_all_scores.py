import os
import argparse
import heapq
import numpy as np
import pandas as pd

from functools import partial

from voxcell import CellCollection


SCORE_CMD = "scorePlacement --annotations {annotations} --rules {rules} --layers {layers}"


def load_morphdb(morphdb_path):
    columns = ['morph', 'layer', 'mtype', 'etype']
    morphdb = pd.read_csv(morphdb_path, sep=r"\s+", names=columns, usecols=columns)
    return [
        ((str(row.layer), row.mtype, row.etype), row.morph)
        for _, row in morphdb.iterrows()
    ]


def load_positions(mvd3_path):
    cells = CellCollection.load(mvd3_path).as_dataframe()
    layer_profile = {
        '1': (1916.807, 2081.756),
        '2': (1767.931, 1916.807),
        '3': (1415.006, 1767.931),
        '4': (1225.434, 1415.006),
        '5': ( 700.378, 1225.434),
        '6': (       0,  700.378),
    }
    return [
        ((str(row.layer), row.mtype, row.etype), (gid, row.y, layer_profile))
        for gid, row in cells.iterrows()
    ]


def drop_key(elem):
    _, v = elem
    return v


def format_candidate(elem, layer_names):
    morph, (id_, y, layer_profile) = elem
    layer_values = " ".join(["%.3f %.3f" % layer_profile[layer] for layer in layer_names])
    return "%s %s %.3f %s" % (morph, id_, y, layer_values)


def parse_score(elem):
    morph, id_, score = elem.split()
    return (id_, (float(score), morph))


def main(morphdb_path, mvd3_path, annotations, rules):
    from pyspark import SparkContext

    layer_names = ['1', '2', '3', '4', '5', '6']

    score_cmd = SCORE_CMD.format(
        annotations=annotations,
        rules=rules,
        layers=",".join(layer_names)
    )

    sc = SparkContext()

    morphdb = sc.parallelize(load_morphdb(morphdb_path))
    positions = sc.parallelize(load_positions(mvd3_path))
    result = (
        morphdb.join(positions)
        .map(drop_key)
        .repartitionAndSortWithinPartitions(1000)
        .map(partial(format_candidate, layer_names=layer_names))
        .pipe(score_cmd, env=os.environ)
        .map(parse_score)
        .groupByKey()
        .mapValues(lambda elem: heapq.nlargest(5, elem))
    )

    print "\n".join(map(str, result.collect()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate placement for varying layer depth profile.")
    parser.add_argument(
        "-m", "--morphdb",
        required=True,
        help="Path to MorphDB file"
    )
    parser.add_argument(
        "-c", "--cells",
        required=True,
        help="Path to MVD3 with cell properties"
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
    args = parser.parse_args()

    main(args.morphdb, args.cells, args.annotations, args.rules)
