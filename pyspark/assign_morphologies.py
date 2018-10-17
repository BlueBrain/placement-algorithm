"""
Assigning 'morphology' property to MVD3 using 'placement hints' approach.
"""

import os
import argparse
import logging
import tempfile
import xml.etree.ElementTree as ET

from collections import defaultdict
from itertools import chain
from functools import partial

import numpy as np

from brainbuilder.utils import bbp
from brainbuilder.cell_orientations import apply_random_rotation
from voxcell import CellCollection, OrientationField
from voxcell.nexus.voxelbrain import Atlas


APP_NAME = "assign-morphologies"

L = logging.getLogger(APP_NAME)

SCORE_CMD = (
    "scorePlacement"
    "  --annotations {annotations}"
    "  --rules {rules}"
    "  --layers {layers}"
)


# MVD3 / MorphDB columns definining partitions
KEY_COLUMNS = ['morphology', 'mtype']


def morph_candidates(elem, positions):
    """ Create (morphology, position) candidates to consider. """
    key, value = elem
    return [(key, p) for p in positions.get(value, [])]


def format_candidate(elem):
    """ Prepare input for `scorePlacement`. """
    (morph, mtype), (id_, position) = elem
    return " ".join(chain([morph, mtype, id_], map(str, position)))


def parse_score(elem):
    """ Parse `scorePlacement` output. """
    morph, id_, score = elem.split()
    return (id_, (morph, float(score)))


def pick_morph(elem, index=None, alpha=1.0, seed=0):
    """ Pick morphologies for all GIDs at given position. """
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
        return [(_id, (None, 0.0)) for _id in ids]


def _coarsen(values, resolution):
    """ Round each value to nearest <integer> * `resolution`. """
    return resolution * np.round(values / resolution).astype(np.int)


def get_positions(cells, atlas, layers, resolution, join_columns):
    """
    Get cell positions for `scorePlacement` from CellCollection.

    1) using '[PH]y' and '[PH]<X>' volumetric data, where <X> are layer names,
       get cell position 'y' and layer boundaries '<X>_[0|1]'
       along brain region "principal axis";
    2) coarsen these values, rounding them to `resolution`;
       the bigger the value of resolution is, the fewer positions we have to consider
    3) group GIDs with similar (join_columns, 'y', '<X>_[0|1]') together,
       to consider each unique position only once

    Args:
        cells: voxcell.CellCollection
        layers: list of layer names
        atlas: voxcell.nexus.voxelbrain.Atlas
        resolution: thickness resolution (um)

    Returns:
        (positions, gid_index) tuple, where:
           `positions`: join_columns -> [(group_id, y, <X>_0, <X>_1,...)]
           `gid_index`: group_id -> [index in CellCollection]

    """
    df = cells.properties[join_columns].copy()

    # cell position along brain region "principal axis"
    df['y'] = atlas.load_data('[PH]y').lookup(cells.positions)

    # layer boundaries along brain region "principal axis"
    # '0' correspond to "lower" boundary (fraction 0.0 in placement rules);
    # '1' correspond to "upper" boundary (fraction 1.0 in placement rules)
    for layer in layers:
        y01 = atlas.load_data('[PH]%s' % layer).lookup(cells.positions)
        df['%s_0' % layer] = y01[:, 0]
        df['%s_1' % layer] = y01[:, 1]

    pos_columns = sum([['%s_0' % x, '%s_1' % x] for x in layers], ['y'])
    for c in pos_columns:
        df[c] = _coarsen(df[c], resolution)

    positions = defaultdict(list)
    gid_index = {}

    grouped = df.groupby(join_columns + pos_columns)
    for k, (key_pos, group) in enumerate(grouped):
        _id = "c%d" % k
        key = key_pos[:len(join_columns)]
        pos = key_pos[len(join_columns):]
        positions[key].append((_id, pos))
        gid_index[_id] = group.index.values

    return dict(positions), gid_index


def assign_morphologies(positions, gid_index, layers, morphdb, join_columns, args):
    """
    Assign morphologies to GIDs specified by (positions, gid_index).

    Returns:
        List of (GID, (morphology, score)) tuples, where:
          `GID` is cell index in CellCollection
          `morphology` is morphology name or None if no morphology gets positive score
          `score` is morphology placement score at given cell position
    """
    from pyspark import SparkContext

    score_cmd = SCORE_CMD.format(
        annotations=args.annotations,
        rules=args.rules,
        layers=",".join(layers)
    )

    sc = SparkContext(appName=APP_NAME)
    try:
        morphdb = sc.parallelize(
            (tuple(row[KEY_COLUMNS]), tuple(row[join_columns])) for _, row in morphdb.iterrows()
        )
        positions = sc.broadcast(positions).value
        gid_index = sc.broadcast(gid_index).value
        scores = (morphdb
            .distinct()
            .repartitionAndSortWithinPartitions(args.ntasks)
            .flatMap(partial(morph_candidates, positions=positions))
            .map(format_candidate)
            .pipe(score_cmd, env=os.environ)
            .map(parse_score)
            .groupByKey()
        )
        result = (scores
            .flatMap(partial(pick_morph, index=gid_index, alpha=args.alpha, seed=args.seed))
            .sortByKey()
            .collect()
        )
    finally:
        sc.stop()

    return result


def _dump_obj(obj, name, output_dir):
    """ Pickle object for debug purposes. """
    import cPickle
    with open(os.path.join(output_dir, name + ".pickle"), 'wb') as f:
        cPickle.dump(obj, f)


def collect_layer_names(rules):
    result = set()
    for elem in rules.iter('rule'):
        for name in ('y_layer', 'y_min_layer', 'y_max_layer'):
            attr = elem.attrib.get(name)
            if attr is not None:
                result.add(attr)
    return result


def _parse_rotation_group(elem):
    result = []
    for child in elem.getchildren():
        result.append((
            child.attrib['axis'],
            child.attrib['distr']
        ))
    return result


def parse_rotations(rules):
    global_conf = None
    for elem in rules.iter('global_rotation'):
        if global_conf is not None:
            raise BrainBuilderError("Duplicate <global_rotation> element")
        global_conf = _parse_rotation_group(elem)
    mtype_conf = {}
    for elem in rules.iter('mtype_rotation'):
        conf = _parse_rotation_group(elem)
        for mtype in elem.attrib['mtype'].split("|"):
            if mtype in mtype_conf:
                raise BrainBuilderError("Duplicate <mtype_rotation> element for '%s'" % mtype)
            mtype_conf[mtype] = conf
    return global_conf, mtype_conf


def assign_orientations(cells, atlas, rules):
    orientation_field = atlas.load_data('orientation', cls=OrientationField)
    cells.orientations = orientation_field.lookup(cells.positions)
    global_conf, mtype_conf = parse_rotations(rules)
    for mtype, group in cells.properties.groupby('mtype'):
        conf = mtype_conf.get(mtype, global_conf)
        if conf is None:
            continue
        idx = group.index.values
        for axis, distr in conf:
            cells.orientations[idx] = apply_random_rotation(
                cells.orientations[idx], axis=axis, distr=distr
            )


def main(args):
    np.random.seed(args.seed)

    logging.basicConfig(level=logging.WARNING)
    L.setLevel(logging.INFO)

    if args.ignore_etype:
        morphdb = bbp.load_neurondb(args.morphdb)
        join_columns = ['layer', 'mtype']
    else:
        morphdb = bbp.load_neurondb(args.morphdb, with_emodels=True)
        join_columns = ['layer', 'mtype', 'etype']

    cells = CellCollection.load_mvd3(args.mvd3)
    atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)
    rules = ET.parse(args.rules)

    L.info("Assigning cell orientations...")
    assign_orientations(cells, atlas, rules)

    layers = collect_layer_names(rules)

    if args.debug:
        debug_dir = tempfile.mkdtemp(dir=".", prefix=APP_NAME + ".")
        L.info("Dumping debug data to '%s'", debug_dir)

    L.info("Evaluate cell positions along Y-axis...")
    positions, gid_index = get_positions(cells, atlas, layers, args.resolution, join_columns)
    if args.debug:
        _dump_obj(positions, 'positions', debug_dir)
        _dump_obj(gid_index, 'gid_index', debug_dir)

    L.info("Calculate placement score for each morphology-position candidate...")
    morph_score = assign_morphologies(positions, gid_index, layers, morphdb, join_columns, args)
    if args.debug:
        _dump_obj(morph_score, 'morph_score', debug_dir)

    assert len(morph_score) == len(cells.positions)

    L.info("Collect assigned morphologies to MVD3...")
    morph_values = [None] * len(cells.positions)
    for gid, (morph, score) in morph_score:
        if morph is not None:
            morph_values[gid] = str(morph)  # h5py is not happy with numpy.unicode dtype (??)

    cells.properties['morphology'] = morph_values

    not_assigned = np.count_nonzero(cells.properties.isnull())
    if not_assigned > 0:
        L.warn(
            "Could not pick morphologies for %d position(s), dropping them and reindexing",
            not_assigned,
        )
        cells.remove_unassigned_cells()

    cells.save_mvd3(args.output)
    L.info("Done!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Assign morphologies using 'placement hints'."
    )
    parser.add_argument(
        "--mvd3", help="Path to input MVD3 file", required=True
    )
    parser.add_argument(
        "--morphdb", help="Path to MorphDB file", required=True
    )
    parser.add_argument(
        "--atlas", help="Atlas URL", required=True
    )
    parser.add_argument(
        "--atlas-cache", help="Atlas cache folder", default=None
    )
    parser.add_argument(
        "--resolution", help="Y-resolution (um)", type=int, default=10
    )
    parser.add_argument(
        "--annotations", help="Path to annotations folder", required=True
    )
    parser.add_argument(
        "--rules", help="Path to placement rules file", required=True,
    )
    parser.add_argument(
        "--ignore-etype",
        help="Take 'etype' into account on join",
        action="store_true"
    )
    parser.add_argument(
        "--alpha",
        help="Use `score ** alpha` as morphology choice probability (default: %(default)s)",
        type=float,
        default=1.0
    )
    parser.add_argument(
        "--seed",
        help="Random number generator seed (default: %(default)s)",
        type=int,
        default=0
    )
    parser.add_argument(
        "--ntasks",
        help="Number of Spark tasks to use for scoring (default: %(default)s)",
        type=int,
        default=100
    )
    parser.add_argument(
        "--debug",
        help="Dump additional output for debugging",
        action="store_true"
    )
    parser.add_argument(
        "-o", "--output", help="Path to output MVD3 file", required=True
    )

    main(parser.parse_args())
