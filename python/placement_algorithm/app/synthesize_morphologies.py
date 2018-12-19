#!/usr/bin/env python

"""
- launch TMD(?) synthesis in parallel
- write each synthesized morphology to a separate file
- assign morphology names to MVD3
- assign identity cell rotations to MVD3
- optional axon grafting "on-the-fly"
"""

import argparse
import logging

import numpy as np
import pandas as pd

import morph_tool.transform as mt
from morph_tool.graft import find_axon, graft_axon
from morph_tool.loader import MorphLoader

from voxcell import CellCollection
from voxcell.nexus.voxelbrain import Atlas

from region_grower.context import SpaceContext  # pylint: disable=import-error
from tns import NeuronGrower  # pylint: disable=import-error

from placement_algorithm.app import utils
from placement_algorithm.app.mpi_app import MasterApp, WorkerApp


LOGGER = logging.getLogger('synthesize-morphologies')


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
        return parser.parse_args()

    @property
    def logger(self):
        """ Application logger. """
        return LOGGER

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

    def _check_morph_list(self, filepath):
        """ Check morphology list for N/A morphologies. """
        morph_list = utils.load_morphology_list(filepath, check_gids=self.task_ids)
        if morph_list['morphology'].isnull().any():
            raise RuntimeError("""
                Morphology list has N/A morphologies for some positions.
            """)

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
        logging.basicConfig(level=logging.ERROR)
        self.logger.setLevel(logging.INFO)

        LOGGER.info("Preparing morphology output folder...")
        morph_writer = utils.MorphWriter(args.out_morph_dir, args.out_morph_ext)
        morph_writer.prepare()

        self.logger.info("Loading CellCollection...")
        self.cells = CellCollection.load_mvd3(args.mvd3)

        self._check_tmd_parameters(args.tmd_parameters)
        self._check_tmd_distributions(args.tmd_distributions)
        if args.morph_axon is not None:
            self._check_morph_list(args.morph_axon)

        # Fetch required datasets from VoxelBrain if necessary,
        # so that when workers need them, they can get them directly from disk
        # without a risk of race condition for download.
        self.logger.info("Fetching atlas data...")
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
        self.cells.properties['morphology'] = pd.Series(result)
        # cell orientation is imbued in synthesized morphologies
        self.cells.orientations = np.broadcast_to(
            np.identity(3), (len(self.cells.positions), 3, 3)
        )
        self.logger.info("Export to MVD3...")
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
        result = self.morph_cache.get(rec['morphology']).as_mutable()
        mt.rotate(result, utils.random_rotation_y(n=1)[0])
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
        seed = hash((self.seed, gid)) % (1 << 32)
        np.random.seed(seed)
        morph = self._synthesize(
            xyz=self.cells.positions[gid],
            mtype=self.cells.properties['mtype'][gid]
        )
        if self.axon_morph_list is not None:
            axon_morph = self._load_morphology(self.axon_morph_list, gid)
            graft_axon(morph, find_axon(axon_morph))
        return self.morph_writer(morph, gid)


def main():
    """ Application entry point. """
    from placement_algorithm.app.mpi_app import run
    run(Master)


if __name__ == '__main__':
    main()
