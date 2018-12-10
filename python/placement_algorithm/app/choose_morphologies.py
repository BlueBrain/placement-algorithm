#!/usr/bin/env python

"""
Assign morphologies (along with their orientations) using placement hints approach.
"""

import argparse
import itertools
import logging

import numpy as np
import pandas as pd
import ujson

from voxcell import CellCollection, OrientationField
from voxcell.nexus.voxelbrain import Atlas

from mpi4py import MPI  # pylint: disable=import-error

from placement_algorithm import files, algorithm


COMM = MPI.COMM_WORLD

MASTER_RANK = 0

LOGGER = logging.getLogger('choose-morphologies')


def _exit(msg):
    import sys
    LOGGER.error(msg)
    sys.exit(1)


def _load_json(filepath):
    with open(filepath) as f:
        return ujson.load(f)


def _fetch_atlas_data(atlas, layer_names, memcache=False):
    """ Fetch '[PH]' datasets to disk; cache in memory if needed. """
    for dset in itertools.chain(['y'], layer_names):
        atlas.load_data('[PH]%s' % dset, memcache=memcache)


def _bind_annotations(annotations, morphdb, rules):
    """
    Bind "raw" annotations to corresponding mtype rules.

    Args:
        annotations: {morphology -> {rule -> {param -> value}}} dict
        morphdb: MorphDB as pandas DataFrame
        rules: files.PlacementRules instance

    Returns:
        {metype -> (rules, params)}, where `params` is
        pandas DataFrame with annotation params for morphologies
        from `morphdb` corresponding to `metype`.
    """
    result = {}
    for (mtype, etype), group in morphdb.groupby(['mtype', 'etype']):
        mtype_annotations = {
            m: annotations[m] for m in group['morphology'].unique()
        }
        result[(mtype, etype)] = rules.bind(mtype_annotations, mtype)
    return result


def _rotate_around_y(A):
    """
    Apply random rotations around Y axis to a list of rotation matrices.

    Args:
        A: NumPy array of shape N x 3 x 3

    Returns:
        NumPy array [rotate(A[k]) for k in range(N)]
    """
    # copied from `brainbuilder.cell_orientations` to avoid a heavy dependency
    # consider reusing `brainbuilder` methods if we need something more general
    # (like user-defined distributions for rotation angles)
    from voxcell.math_utils import angles_to_matrices
    angles = np.random.uniform(-np.pi, np.pi, size=A.shape[0])
    rotations = angles_to_matrices(angles, axis='y')
    return np.einsum('...ij,...jk->...ik', A, rotations)


def _assign_orientations(cells, atlas):
    """
    Assign cell orientations to CellCollection based on atlas orientation field.

    Apply random rotation around Y-axis.

    Args:
        cells: CellCollection to be augmented
        atlas: VoxelBrain atlas with 'orientation' dataset

    No return value; `cells` is input/output argument.
    """
    orientation_field = atlas.load_data('orientation', cls=OrientationField)
    cells.orientations = _rotate_around_y(
        orientation_field.lookup(cells.positions)
    )


def _assign_morphologies(cells, morphologies, dropna):
    """
    Assign morphologies to CellCollection.

    Args:
        cells: CellCollection to be augmented
        morphologies: dictionary {gid -> morphology_name}
        dropna: if True, drop cells with `None` morphology (otherwise: fatal error)

    No return value; `cells` is input/output argument.
    """
    cells.properties['morphology'] = pd.Series(morphologies)
    na_mask = cells.properties['morphology'].isnull()
    if na_mask.any():
        LOGGER.warn("Failed to pick morphologies for %d position(s)", np.count_nonzero(na_mask))
        dropped = cells.properties[na_mask]['mtype'].value_counts()
        overall = cells.properties['mtype'].value_counts()
        drop_ratio = pd.DataFrame({
            'failed': dropped,
            'out of': overall,
        }).dropna().astype(int)
        drop_ratio['ratio, %'] = 100.0 * drop_ratio['failed'] / drop_ratio['out of']
        drop_ratio.sort_values('ratio, %', ascending=False, inplace=True)
        LOGGER.info("Failure ratio by mtypes:\n%s", drop_ratio.to_string(float_format="%.1f"))
        if dropna:
            LOGGER.info("Dropping cells with no morphologies assigned and reindexing")
            cells.remove_unassigned_cells()
            cells.properties.reset_index(inplace=True, drop=True)
        else:
            _exit("""
                Could not assign morphologies for some positions.
                Please re-run with `--dropna` if it's OK to drop such positions.
            """)


def run_master(args):
    """
    Master (coordinator) logic.

      - parsing input files
      - broadcasting shared data to workers
      - distributing tasks to workers
      - collecting results from workers
      - writing output to MVD3

    Executed on node MPI_RANK == 0.
    """
    from tqdm import tqdm

    logging.basicConfig(level=logging.ERROR)
    LOGGER.setLevel(logging.INFO)

    if COMM.Get_size() < 2:
        _exit("""
            MPI environment should contain at least two nodes;
            rank 0 serves as the coordinator, rank N > 0 -- as task workers.
        """)

    LOGGER.info("Loading placement rules...")
    rules = files.PlacementRules(args.rules)

    LOGGER.info("Loading MorphDB...")
    morphdb = files.parse_morphdb(args.morphdb)

    LOGGER.info("Loading and binding annotations...")
    annotations = _bind_annotations(_load_json(args.annotations), morphdb, rules)

    LOGGER.info("Loading CellCollection...")
    cells = CellCollection.load_mvd3(args.mvd3)

    LOGGER.info("Fetching atlas data...")
    atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)

    # Fetch '[PH]' datasets from VoxelBrain if necessary,
    # so that when workers need them, they can get them directly from disk.
    _fetch_atlas_data(atlas, rules.layer_names)

    LOGGER.info("Assigning cell orientations...")
    _assign_orientations(cells, atlas)

    LOGGER.info("Broadcasting shared data...")
    COMM.bcast((rules.layer_names, annotations), root=MASTER_RANK)

    gids = np.arange(len(cells.positions), dtype=np.uint32)
    worker_count = COMM.Get_size() - 1
    LOGGER.info("Distributing %d tasks across %d worker(s)...", len(gids), worker_count)

    # Some mtypes take longer to process than the others.
    # Distribute GIDs randomly across workers to amortize that.
    np.random.shuffle(gids)

    for rank, chunk in enumerate(np.array_split(gids, worker_count), 1):
        COMM.send(chunk, dest=rank)

    LOGGER.info("Processing tasks...")
    morphologies = dict(
        COMM.recv()
        for _ in tqdm(range(len(gids)))
    )

    _assign_morphologies(cells, morphologies, dropna=args.dropna)

    LOGGER.info("Export to MVD3...")
    cells.save_mvd3(args.out_mvd3)

    LOGGER.info("Done!")


class ChooseMorphology(object):
    """ Helper class for choosing morphologies using placement hints. """
    def __init__(self, atlas, annotations, layer_names, alpha):
        self.atlas = atlas
        self.annotations = annotations
        self.layer_names = layer_names
        self.alpha = alpha

    def _get_profile(self, xyz):
        """ Query layer profile for `xyz` position. """
        result = {}
        result['y'] = self.atlas.load_data('[PH]y').lookup(xyz)
        for layer in self.layer_names:
            y0, y1 = self.atlas.load_data('[PH]%s' % layer).lookup(xyz)
            result['%s_0' % layer] = y0
            result['%s_1' % layer] = y1
        return result

    def __call__(self, xyz, mtype, etype):
        profile = self._get_profile(xyz)
        rules, params = self.annotations[(mtype, etype)]
        return algorithm.choose_morphology(
            profile, rules, params, alpha=self.alpha
        )


def run_worker(args):
    """
    Worker logic.

     - picking morphologies for subset of circuit cells using placement algorithm

    Executed on all MPI_RANK > 0 nodes.
    """

    # Get shared data
    layer_names, annotations = COMM.bcast(None, root=MASTER_RANK)

    # At this point all necessary atlas data should be available from disk
    atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)

    # Cache '[PH]' datasets in memory
    _fetch_atlas_data(atlas, layer_names, memcache=True)

    choose_morphology = ChooseMorphology(atlas, annotations, layer_names, alpha=args.alpha)

    cells = CellCollection.load_mvd3(args.mvd3)

    gids = COMM.recv(source=MASTER_RANK)
    for gid in gids:
        seed = hash((args.seed, gid))
        np.random.seed(seed % (1 << 32))
        morph_name = choose_morphology(
            xyz=cells.positions[gid],
            mtype=cells.properties['mtype'][gid],
            etype=cells.properties['etype'][gid]
        )
        COMM.send((gid, morph_name), dest=MASTER_RANK)


def main():
    """ Application entry point. """
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
        "--annotations", help="Path to JSON with morphology annotations", required=True
    )
    parser.add_argument(
        "--rules", help="Path to placement rules file", required=True,
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
        "--dropna",
        help="Drop positions with no morphologies assigned (default: %(default)s)",
        action="store_true"
    )
    parser.add_argument(
        "--out-mvd3", help="Path to output MVD3 file", required=True
    )

    args = parser.parse_args()

    if COMM.Get_rank() == MASTER_RANK:
        run_master(args)
    else:
        run_worker(args)


if __name__ == '__main__':
    main()
