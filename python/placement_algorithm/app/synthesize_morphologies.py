#!/usr/bin/env python

"""
- launch TMD(?) synthesis in parallel
- write each synthesized morphology to a separate file
- assign morphology names to MVD3
- assign identity cell rotations to MVD3
- optional axon grafting "on-the-fly"
"""

import argparse

import numpy as np

import morph_tool.transform as mt
from morph_tool.graft import graft_axon
from morph_tool.loader import MorphLoader

from voxcell import CellCollection
from voxcell.nexus.voxelbrain import Atlas

from region_grower.context import SpaceContext  # pylint: disable=import-error
from tns import NeuronGrower  # pylint: disable=import-error

from placement_algorithm.app import utils
from placement_algorithm.app.mpi_app import MasterApp, WorkerApp
from placement_algorithm.logger import LOGGER


def _fetch_atlas_data(atlas):
    """ Fetch required datasets to disk. """
    atlas.fetch_data('depth')
    atlas.fetch_data('orientation')
    for layer in range(1, 7):
        atlas.fetch_data('thickness:L%d' % layer)


class Master(MasterApp):
    """ MPI application master task. """
    @staticmethod
    def parse_args():
        """ Parse command line arguments. """
        parser = argparse.ArgumentParser(
            description="Choose morphologies using 'placement hints'."
        )
        parser.add_argument(
            "--mvd3", help="Path to input MVD3 file", required=True
        )
        parser.add_argument(
            "--tmd-parameters", help="Path to JSON with TMD parameters", required=True
        )
        parser.add_argument(
            "--tmd-distributions", help="Path to JSON with TMD distributions", required=True
        )
        parser.add_argument(
            "--morph-axon", help="TSV file with axon morphology list (for grafting)", default=None
        )
        parser.add_argument(
            "--base-morph-dir", help="Path to base morphology release folder", default=None
        )
        parser.add_argument(
            "--atlas", help="Atlas URL", required=True
        )
        parser.add_argument(
            "--atlas-cache", help="Atlas cache folder", default=None
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
            "--out-morph-dir", help="Path to output morphology folder", default=None
        )
        parser.add_argument(
            "--out-morph-ext",
            choices=['h5', 'swc', 'asc'], nargs='+',
            help="Morphology export format(s)",
            default=['h5']
        )
        parser.add_argument(
            "--max-files-per-dir",
            help="Maximum files per level for morphology output folder",
            type=int,
            default=None
        )
        parser.add_argument(
            "--max-drop-ratio",
            help="Max drop ratio for any mtype (default: %(default)s)",
            type=float,
            default=0.0
        )
        return parser.parse_args()

    def _check_has_mtypes(self, content):
        for mtype in self.cells.properties['mtype'].unique():
            if mtype not in content:
                raise RuntimeError("Missing mtype: '%s'" % mtype)

    def _check_tmd_distributions(self, filepath):
        """ Check if TMD distributions are available for all used mtypes. """
        content = utils.load_json(filepath)
        self._check_has_mtypes(content)

    def _check_tmd_parameters(self, filepath):
        """ Check if TMD parameters are available for all used mtypes. """
        content = utils.load_json(filepath)
        if '__default__' in content:
            return
        self._check_has_mtypes(content)

    def _check_morph_list(self, filepath, max_na_ratio):
        """ Check morphology list for N/A morphologies. """
        morph_list = utils.load_morphology_list(filepath, check_gids=self.task_ids)
        utils.check_na_morphologies(
            morph_list, mtypes=self.cells.properties['mtype'], threshold=max_na_ratio
        )

    def setup(self, args):
        """
        Initialize master task.

          - prepare morphology output folder
          - load CellCollection
          - check TMD parameters / distributions
          - check axon morphology list
          - prefetch atlas data
        """
        # pylint: disable=attribute-defined-outside-init

        LOGGER.info("Loading CellCollection...")
        self.cells = CellCollection.load_mvd3(args.mvd3)

        LOGGER.info("Preparing morphology output folder...")
        morph_writer = utils.MorphWriter(args.out_morph_dir, args.out_morph_ext)
        morph_writer.prepare(
            num_files=len(self.cells.positions),
            max_files_per_dir=args.max_files_per_dir
        )

        self._check_tmd_parameters(args.tmd_parameters)
        self._check_tmd_distributions(args.tmd_distributions)
        if args.morph_axon is not None:
            self._check_morph_list(args.morph_axon, max_na_ratio=args.max_drop_ratio)

        # Fetch required datasets from VoxelBrain if necessary,
        # so that when workers need them, they can get them directly from disk
        # without a risk of race condition for download.
        LOGGER.info("Fetching atlas data...")
        _fetch_atlas_data(
            Atlas.open(args.atlas, cache_dir=args.atlas_cache)
        )

        self.args = args

        return Worker(morph_writer)

    @property
    def task_ids(self):
        """ Task IDs (= CellCollection IDs). """
        return self.cells.properties.index.values

    def finalize(self, result):
        """
        Finalize master work.

          - assign 'morphology' property based on workers' result
          - assign 'orientation' property to identity matrix
          - dump CellCollection to MVD3
        """
        LOGGER.info("Assigning CellCollection 'morphology' property...")
        utils.assign_morphologies(self.cells, result)

        LOGGER.info("Assigning CellCollection 'orientation' property...")
        # cell orientations are imbued in synthesized morphologies
        self.cells.orientations = np.broadcast_to(
            np.identity(3), (len(self.cells.positions), 3, 3)
        )

        LOGGER.info("Export to MVD3...")
        self.cells.save_mvd3(self.args.out_mvd3)


class Worker(WorkerApp):
    """ MPI application worker task. """
    def __init__(self, morph_writer):
        self.morph_writer = morph_writer

    def setup(self, args):
        """
        Initialize worker.

          - load CellCollection
          - initialize SpaceContext
          - load TMD parameters and distributions
          - load axon morphology list from TSV
        """
        # pylint: disable=attribute-defined-outside-init
        import morphio
        morphio.set_maximum_warnings(0)  # supress MorphIO warnings on writing files

        self.cells = CellCollection.load_mvd3(args.mvd3)
        self.distributions = utils.load_json(args.tmd_distributions)
        self.parameters = utils.load_json(args.tmd_parameters)
        self.context = SpaceContext(
            Atlas.open(args.atlas, cache_dir=args.atlas_cache)
        )
        self.seed = args.seed

        if args.morph_axon is None:
            self.axon_morph_list = None
        else:
            self.axon_morph_list = utils.load_morphology_list(args.morph_axon)
            self.morph_cache = MorphLoader(args.base_morph_dir, file_ext='h5')

    def _get_distributions(self, mtype):
        return self.distributions[mtype]

    def _get_parameters(self, xyz, mtype):
        if mtype not in self.parameters:
            mtype = '__default__'
        params = self.parameters[mtype]
        return self.context.get_corrected_params(params, xyz)

    def _synthesize(self, xyz, mtype):
        """
        Synthesize soma + dendritic tree.

        Returns:
            morphio.mut.Morphology instance.
        """
        grower = NeuronGrower(
            input_parameters=self._get_parameters(xyz, mtype),
            input_distributions=self._get_distributions(mtype)
        )
        return grower.grow()

    def _load_morphology(self, morph_list, gid):
        """
        Load morphology corresponding to `gid`.

         - apply random rotation around Y-axis

        Returns:
            morphio.mut.Morphology instance.
        """
        rec = morph_list.loc[gid]
        if rec['morphology'] is None:
            return None
        result = self.morph_cache.get(rec['morphology']).as_mutable()
        transform = np.identity(4)
        transform[:3, :3] = utils.random_rotation_y(n=1)[0]
        if 'scale' in rec:
            transform = np.identity(4)
            transform[1, :] *= rec['scale']  # scale along Y-axis
        mt.transform(result, transform)
        return result

    def __call__(self, gid):
        """
        Synthesize morphology for given GID.

          - launch NeuronGrower to synthesize soma and dendrites
          - load axon morphology, if needed, and do axon grafting
          - export result to file

        Returns:
            Generated filename (unique by GID).
        """
        axon_morph = None
        if self.axon_morph_list is not None:
            axon_morph = self._load_morphology(self.axon_morph_list, gid)
            if axon_morph is None:
                # no donor axon => drop position
                return None
        seed = hash((self.seed, gid)) % (1 << 32)
        np.random.seed(seed)
        morph = self._synthesize(
            xyz=self.cells.positions[gid],
            mtype=self.cells.properties['mtype'][gid]
        )
        if axon_morph is not None:
            graft_axon(morph, axon_morph)
        return self.morph_writer(morph, seed=seed)


def main():
    """ Application entry point. """
    utils.setup_logger()
    from placement_algorithm.app.mpi_app import run
    run(Master)


if __name__ == '__main__':
    main()
