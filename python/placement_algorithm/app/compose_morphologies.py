#!/usr/bin/env python

"""
Assign synthesized morphologies, grafting axons chosen with placement hints approach.
"""

import os
import argparse
import itertools
import logging

import numpy as np
import pandas as pd
import ujson

import morphio

from voxcell import CellCollection, OrientationField
from voxcell.nexus.voxelbrain import Atlas

from mpi4py import MPI  # pylint: disable=import-error

from placement_algorithm import files, algorithm

import placement_algorithm.app.morph_utils as mu


COMM = MPI.COMM_WORLD

MASTER_RANK = 0

LOGGER = logging.getLogger('compose-morphologies')


def _exit(msg):
    import sys
    LOGGER.error(msg)
    sys.exit(1)


def _load_json(filepath):
    with open(filepath) as f:
        return ujson.load(f)


def _morph_name(gid):
    return "a%08d" % (gid + 1)


def _fetch_atlas_data(atlas, layer_names, memcache=False):
    """ Fetch atlas datasets to disk; cache in memory if needed. """
    atlas.load_data('orientation', cls=OrientationField, memcache=memcache)
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
        {mtype -> (rules, params)}, where `params` is
        pandas DataFrame with annotation params for morphologies
        from `morphdb` corresponding to `mtype`.
    """
    result = {}
    for mtype, group in morphdb.groupby('mtype'):
        mtype_annotations = {
            m: annotations[m] for m in group['morphology'].unique()
        }
        result[mtype] = rules.bind(mtype_annotations, mtype)
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
    # pylint: disable=too-many-locals
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
    axon_morphdb = files.parse_morphdb(args.morphdb_axon)
    dend_morphdb = files.parse_morphdb(args.morphdb_dend)

    LOGGER.info("Loading and binding annotations...")
    all_annotations = _load_json(args.annotations)
    axon_annotations = _bind_annotations(all_annotations, axon_morphdb, rules)
    dend_annotations = _bind_annotations(all_annotations, dend_morphdb, rules)

    LOGGER.info("Loading CellCollection...")
    cells = CellCollection.load_mvd3(args.mvd3)

    LOGGER.info("Fetching atlas data...")
    atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)

    # Fetch '[PH]' datasets from VoxelBrain if necessary,
    # so that when workers need them, they can get them directly from disk.
    _fetch_atlas_data(atlas, rules.layer_names)

    LOGGER.info("Broadcasting shared data...")
    COMM.bcast(
        (
            rules.layer_names,
            axon_annotations,
            dend_annotations,
        ),
        root=MASTER_RANK
    )

    gids = np.arange(len(cells.positions), dtype=np.uint32)
    worker_count = COMM.Get_size() - 1
    LOGGER.info("Distributing %d tasks across %d worker(s)...", len(gids), worker_count)

    # Some mtypes take longer to process than the others.
    # Distribute GIDs randomly across workers to amortize that.
    np.random.shuffle(gids)

    for rank, chunk in enumerate(np.array_split(gids, worker_count), 1):
        COMM.send(chunk, dest=rank)

    LOGGER.info("Processing tasks...")
    morphologies = dict([
        COMM.recv()
        for _ in tqdm(range(len(gids)))
    ])

    cells.properties['morphology'] = pd.Series(morphologies)
    cells.orientations = np.broadcast_to(np.identity(3), (len(gids), 3, 3))

    LOGGER.info("Export to MVD3...")
    cells.save_mvd3(args.out_mvd3)

    LOGGER.info("Done!")


class ChooseMorphology(object):
    """ Helper class for choosing morphologies using placement hints. """
    def __init__(self, atlas, annotations, layer_names, alpha, morph_dir):
        self.atlas = atlas
        self.annotations = annotations
        self.layer_names = layer_names
        self.alpha = alpha
        self.morph_dir = morph_dir

    def _get_profile(self, xyz):
        """ Query layer profile for `xyz` position. """
        result = {}
        result['y'] = self.atlas.load_data('[PH]y').lookup(xyz)
        for layer in self.layer_names:
            y0, y1 = self.atlas.load_data('[PH]%s' % layer).lookup(xyz)
            result['%s_0' % layer] = y0
            result['%s_1' % layer] = y1
        return result

    def _get_orientation(self, xyz, randomize_y):
        result = self.atlas.load_data('orientation', cls=OrientationField).lookup(xyz)
        if randomize_y:
            result = _rotate_around_y(result)
        return result

    def _choose_morphology(self, xyz, mtype, segment_type):
        profile = self._get_profile(xyz)
        rules, params = self.annotations[mtype]
        result = algorithm.choose_morphology(
            profile, rules, params, alpha=self.alpha, segment_type=segment_type
        )
        if result is None:
            LOGGER.warn(
                "Can not choose morphology for (%s, %s); picking one at random",
                xyz, mtype
            )
            result = np.random.choice(params.index)
        return result

    def _load_morphology(self, morph_name, mutable=False):
        filepath = os.path.join(self.morph_dir, morph_name + ".h5")
        if mutable:
            return morphio.mut.Morphology(filepath)  # pylint: disable=no-member
        else:
            return morphio.Morphology(filepath)


class ChooseMorphologyBody(ChooseMorphology):
    """ Helper class for choosing soma + dendritic tree using placement hints. """
    def __call__(self, xyz, mtype):
        morph_name = self._choose_morphology(xyz, mtype, segment_type='dendrite')
        result = self._load_morphology(morph_name, mutable=True)
        mu.remove_axon(result)
        mu.apply_rotation(result, self._get_orientation(xyz, randomize_y=True))
        return result


class ChooseMorphologyAxon(ChooseMorphology):
    """ Helper class for choosing axon using placement hints. """
    def __call__(self, xyz, mtype):
        morph_name = self._choose_morphology(xyz, mtype, segment_type='axon')
        morph = self._load_morphology(morph_name, mutable=False)
        result = mu.find_axon(morph)
        mu.apply_rotation(result, self._get_orientation(xyz, randomize_y=True))
        return result


def run_worker(args):
    """
    Worker logic.

     - composing morphologies for subset of circuit cells using placement algorithm

    Executed on all MPI_RANK > 0 nodes.
    """
    # pylint: disable=too-many-locals
    atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)

    layer_names, axon_annotations, dend_annotations = COMM.bcast(None, root=MASTER_RANK)

    # At this point all necessary atlas datasets should be available from disk
    atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)

    # Cache atlas datasets in memory
    _fetch_atlas_data(atlas, layer_names, memcache=True)

    make_body = ChooseMorphologyBody(
        atlas, dend_annotations, layer_names, alpha=args.alpha, morph_dir=args.base_morph_dir
    )

    make_axon = ChooseMorphologyAxon(
        atlas, axon_annotations, layer_names, alpha=args.alpha, morph_dir=args.base_morph_dir
    )

    cells = CellCollection.load_mvd3(args.mvd3)

    gids = COMM.recv(source=MASTER_RANK)

    for gid in gids:
        xyz = cells.positions[gid]
        mtype = cells.properties['mtype'][gid]
        seed = hash((args.seed, gid))
        np.random.seed(seed % (1 << 32))
        morph = make_body(xyz, mtype)
        axon = make_axon(xyz, mtype)
        mu.graft_axon(morph, axon)
        morph_name = _morph_name(gid)
        for ext in set(args.out_morph_ext):
            morph.write(os.path.join(args.out_morph_dir, morph_name + "." + ext))
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
        "--morphdb-axon",
        help="Path to MorphDB file with morphologies used as axon donors",
        required=True
    )
    parser.add_argument(
        "--morphdb-dend",
        help="Path to MorphDB file with morphologies used as dendrite / soma donors",
        required=True
    )
    parser.add_argument(
        "--base-morph-dir", help="Path to base morphology release folder", required=True
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
        "--out-mvd3", help="Path to output MVD3 file", required=True
    )
    parser.add_argument(
        "--out-morph-dir", help="Path to output morphology folder", required=True
    )
    parser.add_argument(
        "--out-morph-ext",
        choices=['h5', 'swc', 'asc'], nargs='+',
        help="Morphology export format(s)",
        default="h5"
    )

    args = parser.parse_args()

    if COMM.Get_rank() == MASTER_RANK:
        run_master(args)
    else:
        run_worker(args)


if __name__ == '__main__':
    main()
