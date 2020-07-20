#!/usr/bin/env python

"""
- launch TMD(?) synthesis in parallel
- write each synthesized morphology to a separate file
- assign morphology names to MVD3
- assign identity cell rotations to MVD3
- optional axon grafting "on-the-fly"
"""

import argparse
from typing import Dict, Optional

import yaml
from morphio.mut import Morphology

import attr
import numpy as np

from voxcell import OrientationField
from voxcell.nexus.voxelbrain import Atlas
from region_grower.context import SpaceContext
import morph_tool.transform as mt
from morph_tool.graft import graft_axon
from morph_tool.loader import MorphLoader
from tns import TNSError

from placement_algorithm.app import utils
from placement_algorithm.exceptions import SkipSynthesisError
from placement_algorithm.app.mpi_app import MasterApp, WorkerApp
from placement_algorithm.logger import LOGGER


@attr.s
class WorkerResult:
    '''The container class for that has to be the returned type of Worker.__call__'''
    #: The morphology name
    name = attr.ib(type=str)

    #: The list coordinates where the apical tufts are starting
    apical_points = attr.ib(type=[])


class Master(MasterApp):
    """ MPI application master task. """
    def __init__(self):
        self.cells = None  # type: Optional[CellCollection]
        self.args = None

    @staticmethod
    def parse_args():
        """ Parse command line arguments. """
        parser = argparse.ArgumentParser(
            description="Choose morphologies using 'placement hints'."
        )
        parser.add_argument(
            "--mvd3", help="Deprecated! Path to input MVD3 file. Use --cells-path instead."
        )
        parser.add_argument(
            "--cells-path", help="Path to a file storing cells collection"
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
            "--out-apical", help=("Path to output YAML apical file containing"
                                  " the coordinates where apical dendrites are tufting"),
            required=True
        )
        parser.add_argument(
            "--out-morph-dir", help="Path to output morphology folder", default='out'
        )
        parser.add_argument(
            "--out-morph-ext",
            choices=['swc', 'asc', 'h5'], nargs='+',
            help="Morphology export format(s)",
            default=['swc']
        )
        parser.add_argument(
            "--max-files-per-dir",
            help="Maximum files per level for morphology output folder",
            type=int,
            default=None
        )
        parser.add_argument(
            "--overwrite",
            help="Overwrite output morphology folder (default: %(default)s)",
            action="store_true"
        )
        parser.add_argument(
            "--max-drop-ratio",
            help="Max drop ratio for any mtype (default: %(default)s)",
            type=float,
            default=0.0
        )
        parser.add_argument(
            "--no-mpi",
            help="Do not use MPI and run everything on a single core.",
            action='store_true',
        )
        return parser.parse_args()

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
        LOGGER.info("Loading CellCollection...")
        self.cells = utils.load_cells(args.cells_path, args.mvd3)

        LOGGER.info("Preparing morphology output folder...")
        morph_writer = utils.MorphWriter(args.out_morph_dir, args.out_morph_ext)
        morph_writer.prepare(
            num_files=len(self.cells.positions),
            max_files_per_dir=args.max_files_per_dir,
            overwrite=args.overwrite
        )

        if args.morph_axon is not None:
            self._check_morph_list(args.morph_axon, max_na_ratio=args.max_drop_ratio)

        LOGGER.info("Verifying atlas data and synthesis parameters...")
        # Along the way, this check fetches required datasets from VoxelBrain if necessary,
        # so that when workers need them, they can get them directly from disk
        # without a risk of race condition for download.
        atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)
        SpaceContext(
            atlas=atlas,
            tmd_distributions_path=args.tmd_distributions,
            tmd_parameters_path=args.tmd_parameters
        ).verify(mtypes=self.cells.properties['mtype'].unique())

        self.args = args

        return Worker(morph_writer)

    @property
    def task_ids(self):
        """ Task IDs (= CellCollection IDs). """
        return self.cells.properties.index.values

    def finalize(self, result: Dict[int, WorkerResult]):
        """
        Finalize master work.

          - assign 'morphology' property based on workers' result
          - assign 'orientation' property to identity matrix
          - dump CellCollection to MVD3

        Args:
            result: A dict {gid -> WorkerResult}
        """
        LOGGER.info("Assigning CellCollection 'morphology' property...")

        utils.assign_morphologies(self.cells,
                                  {gid: item.name for gid, item in result.items()})

        LOGGER.info("Assigning CellCollection 'orientation' property...")
        # cell orientations are imbued in synthesized morphologies
        self.cells.orientations = np.broadcast_to(
            np.identity(3), (len(self.cells.positions), 3, 3)
        )

        LOGGER.info("Export to MVD3...")
        self.cells.save_mvd3(self.args.out_mvd3)

        def first_non_None(apical_points):
            '''Returns the first non None apical coordinates'''
            for coord in apical_points:
                if coord is not None:
                    return coord.tolist()
            return None

        with open(self.args.out_apical, 'w') as apical_file:
            yaml.dump({item.name: first_non_None(item.apical_points)
                       for item in result.values()},
                      apical_file)


class Worker(WorkerApp):
    """ MPI application worker task. """
    def __init__(self, morph_writer):
        self.morph_writer = morph_writer
        self.max_synthesis_attempts_count = 10

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

        atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)

        self.cells = utils.load_cells(args.cells_path, args.mvd3)
        self.context = SpaceContext(
            atlas=atlas,
            tmd_distributions_path=args.tmd_distributions,
            tmd_parameters_path=args.tmd_parameters
        )
        self.orientation = atlas.load_data('orientation', cls=OrientationField)
        self.seed = args.seed

        if args.morph_axon is None:
            self.axon_morph_list = None
        else:
            self.axon_morph_list = utils.load_morphology_list(args.morph_axon)

            # When no_mpi == True, dask is used, and it can't pickle the lru_cache
            # so we disable it
            cache_size = None if not args.no_mpi else 0
            self.morph_cache = MorphLoader(args.base_morph_dir, file_ext='h5',
                                           cache_size=cache_size)

    def _load_morphology(self, morph_list, gid, xyz) -> Optional[Morphology]:
        """Returns the morphology corresponding to gid if found

        The morphology is then scaled, rotated around Y and
        aligned according to the orientation field
        """
        if morph_list is None:
            return None

        rec = morph_list.loc[gid]
        if rec['morphology'] is None:
            raise SkipSynthesisError(f'gid {gid} not found in morph_list')

        name = rec['morphology']
        morph = self.morph_cache.get(name)
        if morph is None:
            raise SkipSynthesisError(f'Unable to find the morphology {name}')

        morph = morph.as_mutable()
        transform = np.identity(4)
        transform[:3, :3] = np.matmul(
            self.orientation.lookup(xyz)[0],
            utils.random_rotation_y(n=1)[0]
        )
        scale = rec.get('scale')
        if scale is not None:
            transform = scale * transform
        mt.transform(morph, transform)

        return morph

    def _attempt_synthesis(self, xyz, mtype):
        for _ in range(self.max_synthesis_attempts_count):
            try:
                return self.context.synthesize(position=xyz, mtype=mtype)
            except TNSError:
                pass
        raise SkipSynthesisError('Too many attempts at synthesizing cell with TNS')

    def __call__(self, gid):
        """
        Synthesize morphology for given GID.

          - launch NeuronGrower to synthesize soma and dendrites
          - load axon morphology, if needed, and do axon grafting
          - export results to file
          - find the NRN section ID of the apical point

        Returns:
            A WorkerResult object
        """
        seed = hash((self.seed, gid)) % (1 << 32)
        xyz = self.cells.positions[gid]
        np.random.seed(seed)

        axon_morph = self._load_morphology(self.axon_morph_list, gid, xyz)

        results = self._attempt_synthesis(xyz, mtype=self.cells.properties['mtype'][gid])
        if axon_morph is not None:
            graft_axon(results.neuron, axon_morph)

        return WorkerResult(name=self.morph_writer(results.neuron, seed=seed),
                            apical_points=results.apical_points)


def main():
    """Application entry point."""
    utils.setup_logger()
    from placement_algorithm.app.mpi_app import run
    run(Master)


if __name__ == '__main__':
    main()
