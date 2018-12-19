#!/usr/bin/env python

"""
- assign morphologies from pre-generated TSV list to MVD3
- assign cell orientations to MVD3
  (orientation field + random rotation around Y axis)
- write only morphology names to MVD3 (previous approach);
  or write separate morphology file per GID ("instantiate")
- optional axon grafting "on-the-fly"
"""

import argparse
import logging

import numpy as np
import pandas as pd

from morph_tool.graft import find_axon, graft_axon
from morph_tool.loader import MorphLoader

from voxcell import CellCollection, OrientationField
from voxcell.nexus.voxelbrain import Atlas

from placement_algorithm.app import utils
from placement_algorithm.app.mpi_app import MasterApp, WorkerApp


LOGGER = logging.getLogger('assign-morphologies')


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
    cells.orientations = utils.multiply_matrices(
        orientation_field.lookup(cells.positions),
        utils.random_rotation_y(n=len(cells.positions))
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
        assert dropna
        LOGGER.info(
            "Dropping %d cells with no morphologies assigned; reindexing",
            np.count_nonzero(na_mask)
        )
        cells.remove_unassigned_cells()


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
            "--morph", help="TSV file with morphology list", required=True
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
            "--dropna",
            help="Drop positions with no morphologies assigned (default: %(default)s)",
            action="store_true"
        )
        parser.add_argument(
            "--instantiate",
            help="Write morphology files (default: %(default)s)",
            action="store_true"
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
        return parser.parse_args()

    @property
    def logger(self):
        """ Application logger. """
        return LOGGER

    def _check_morph_list(self, filepath, allow_na):
        morph_list = utils.load_morphology_list(filepath, check_gids=self.task_ids)
        if not allow_na and morph_list['morphology'].isnull().any():
            raise RuntimeError("""
                Morphology list has N/A morphologies for some positions.
                Please re-run with `--dropna` if it's OK to drop such positions.
            """)

    def setup(self, args):
        """
        Initialize master.

          - prepare morphology output folder
          - load CellCollection
          - assign cell orientations
          - check morphology lists for not assigned morphologies
          - prefetch atlas data
        """
        # pylint: disable=attribute-defined-outside-init
        logging.basicConfig(level=logging.ERROR)
        self.logger.setLevel(logging.INFO)

        LOGGER.info("Loading CellCollection...")
        self.cells = CellCollection.load_mvd3(args.mvd3)

        if args.instantiate:
            LOGGER.info("Preparing morphology output folder...")
            morph_writer = utils.MorphWriter(args.out_morph_dir, args.out_morph_ext)
            morph_writer.prepare(
                num_files=len(self.cells.positions),
                max_files_per_dir=args.max_files_per_dir
            )
        else:
            morph_writer = None

        LOGGER.info("Assigning CellCollection 'orientation' property...")
        atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)
        _assign_orientations(self.cells, atlas)

        LOGGER.info("Verifying morphology list(s)...")
        self._check_morph_list(args.morph, allow_na=args.dropna)
        if args.morph_axon is not None:
            self._check_morph_list(args.morph_axon, allow_na=args.dropna)

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
          - dump CellCollection to MVD3
        """
        LOGGER.info("Assigning CellCollection 'morphology' property...")
        _assign_morphologies(self.cells, result, dropna=self.args.dropna)

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
          - load morphology list(s) from TSV
        """
        # pylint: disable=attribute-defined-outside-init
        import morphio
        morphio.set_maximum_warnings(0)  # supress MorphIO warnings on writing files

        self.cells = CellCollection.load_mvd3(args.mvd3)
        self.morph_cache = MorphLoader(args.base_morph_dir, file_ext='h5')
        self.morph_list = utils.load_morphology_list(args.morph)
        if args.morph_axon is None:
            self.morph_list_axon = None
        else:
            self.morph_list_axon = utils.load_morphology_list(args.morph_axon)

    def _load_morphology(self, morph_list, gid):
        """
        Load morphology corresponding to `gid`.

        Returns:
            morphio.mut.Morphology instance.
        """
        rec = morph_list.loc[gid]
        if rec['morphology'] is None:
            return None
        result = self.morph_cache.get(rec['morphology']).as_mutable()
        return result

    def __call__(self, gid):
        """
        Instantiate morphology for given GID.

          - load morphology from morph list
          - load axon morphology, if needed, and do axon grafting
          - export result to file

        Returns:
            Generated filename (unique by GID).
        """
        morph = self._load_morphology(self.morph_list, gid)
        if morph is None:
            return None
        if self.morph_list_axon is not None:
            axon_morph = self._load_morphology(self.morph_list_axon, gid)
            if axon_morph is None:
                return None
            graft_axon(morph, find_axon(axon_morph))
        return self.morph_writer(morph, seed=gid)


def main():
    """ Application entry point. """
    args = Master.parse_args()
    if args.instantiate:
        if args.base_morph_dir is None:
            raise RuntimeError(
                "`--base-morph-dir` is required for instantiating morphologies"
            )
        if args.out_morph_dir is None:
            raise RuntimeError(
                "`--out-morph-dir` is required for instantiating morphologies"
            )
        from placement_algorithm.app.mpi_app import run
        run(Master)
    else:
        if args.out_morph_dir is not None:
            raise RuntimeError(
                "`--out-morph-dir` not needed for writing MVD3 w/o instantiating morphologies"
            )
        if args.morph_axon is not None:
            raise RuntimeError(
                "`--morph-axon` should be used with `--instantiate`"
            )
        app = Master()
        app.setup(args)
        morph_list = utils.load_morphology_list(args.morph)
        app.finalize(morph_list['morphology'])


if __name__ == '__main__':
    main()
