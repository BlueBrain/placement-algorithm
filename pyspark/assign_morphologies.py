"""
Assigning 'morphology' property to MVD3 using 'placement hints' approach.
"""

import os
import argparse
import logging
import tempfile

from collections import defaultdict
from itertools import chain
from functools import partial

import numpy as np

from brainbuilder.utils import bbp
from brainbuilder.nexus.voxelbrain import Atlas
from voxcell import CellCollection


APP_NAME = "assign-morphologies"

L = logging.getLogger(APP_NAME)

SCORE_CMD = (
    "scorePlacement"
    "  --annotations {annotations}"
    "  --rules {rules}"
    "  --layers {layers}"
    "  --profile {profile}"
)


# Columns definining partitions
KEY_COLUMNS = ['morphology', 'mtype']

# Columns to join on between cell positions and MorphDB
JOIN_COLUMNS = ['region', 'mtype', 'etype']


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


def get_positions(cells, atlas, resolution):
    """
    Get cell positions for `scorePlacement` from CellCollection.

    1) using 'distance' and 'height' volumentric data,
       get cell position 'y' along brain region Y-axis
       and total thickness along 'h' the same axis
    2) coarsen these values, rounding them to `resolution`;
       the bigger the value of resolution is, the fewer positions we have to consider
    3) group GIDs with similar (JOIN_COLUMNS, 'y', 'h') together,
       to consider each unique position only once

    Args:
        cells: voxcell.CellCollection
        atlas: brainbuilder.nexus.voxelbrain.Atlas
        resolution: thickness resolution (um)

    Returns:
        (positions, gid_index) tuple, where:
           `positions`: JOIN_COLUMNS -> [(group_id, y, h)]
           `gid_index`: group_id -> [index in CellCollection]

    """
    distance = atlas.load_data('distance')
    height = atlas.load_data('height')

    df = cells.properties[JOIN_COLUMNS].copy()

    df['y'] = _coarsen(distance.lookup(cells.positions), resolution)
    df['h'] = _coarsen(height.lookup(cells.positions), resolution)

    positions = defaultdict(list)
    gid_index = {}

    grouped = df.groupby(JOIN_COLUMNS +['y', 'h'])
    for k, (key_pos, group) in enumerate(grouped):
        _id = "c%d" % k
        key = key_pos[:len(JOIN_COLUMNS)]
        pos = key_pos[len(JOIN_COLUMNS):]
        positions[key].append((_id, pos))
        gid_index[_id] = group.index.values

    return dict(positions), gid_index


def assign_morphologies(positions, gid_index, morphdb, args):
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
        layers=args.layers,
        profile=args.layer_ratio
    )

    sc = SparkContext(appName=APP_NAME)
    try:
        morphdb = sc.parallelize(
            (tuple(row[KEY_COLUMNS]), tuple(row[JOIN_COLUMNS])) for _, row in morphdb.iterrows()
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


def main(args):
    logging.basicConfig(level=logging.WARNING)
    L.setLevel(logging.INFO)

    morphdb = bbp.load_neurondb_v3(args.morphdb)

    cells = CellCollection.load(args.mvd3)
    atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)

    if args.debug:
        debug_dir = tempfile.mkdtemp(dir=".", prefix=APP_NAME + ".")
        L.info("Dumping debug data to '%s'", debug_dir)

    L.info("Evaluate cell positions along Y-axis...")
    positions, gid_index = get_positions(cells, atlas, args.resolution)
    if args.debug:
        _dump_obj(positions, 'positions', debug_dir)
        _dump_obj(gid_index, 'gid_index', debug_dir)

    L.info("Calculate placement score for each morphology-position candidate...")
    morph_score = assign_morphologies(positions, gid_index, morphdb, args)
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

    cells.save(args.output)
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
        "--layers", help="Layer names ('bottom' to 'top', comma-separated)", required=True
    )
    parser.add_argument(
        "--layer-ratio", help="Layer thickness ratio (comma-separated)", required=True
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
