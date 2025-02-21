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

import numpy as np
import pandas as pd

import morph_tool.transform as mt
from morph_tool.graft import find_axon, graft_axon
from morph_tool.loader import MorphLoader
from voxcell import OrientationField
from voxcell.nexus.voxelbrain import Atlas

from placement_algorithm.app import utils
from placement_algorithm.app.mpi_app import MasterApp, WorkerApp
from placement_algorithm.logger import LOGGER
from placement_algorithm.rotation import assign_orientations
from placement_algorithm.utils import resource_path
from placement_algorithm.validation import validate_config


class Master(MasterApp):
    """ MPI application master task. """
    @staticmethod
    def parse_args():
        """ Parse command line arguments. """
        parser = argparse.ArgumentParser(
            description="Assign morphologies from a list of cells IDs and morphologies."
        )
        parser.add_argument(
            "--mvd3", help="Deprecated! Path to input MVD3 file. Use --cells-path instead."
        )
        parser.add_argument(
            "--cells-path", help="Path to a file storing cells collection"
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
            "--instantiate",
            help="Write morphology files (default: %(default)s)",
            action="store_true"
        )
        parser.add_argument(
            "--out-mvd3", help="Deprecated! Path to output MVD3 file. Use --out-cells-path instead."
        )
        parser.add_argument(
            "--out-cells-path", help="Path to output cells file."
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
            "--rotations",
            help="Path to the configuration file used for rotations. "
                 "If the file is not specified, apply by default "
                 "a random rotation with uniform angle distribution around "
                 "the Y-axis (the principal direction of the morphology)."
        )
        parser.add_argument(
            "--no-mpi",
            help="Do not use MPI and run everything on a single core.",
            action='store_true',
        )
        return parser.parse_args()

    def _check_morph_lists(self, filepaths, max_na_ratio):
        morph_list = pd.DataFrame(index=self.task_ids)
        for name, filepath in filepaths.items():
            if filepath is not None:
                morph_list[name] = utils.load_morphology_list(
                    filepath, check_gids=self.task_ids
                )['morphology']
        utils.check_na_morphologies(
            morph_list, mtypes=self.cells.properties['mtype'], threshold=max_na_ratio
        )

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

        LOGGER.info("Loading CellCollection...")
        self.cells = utils.load_cells(args.cells_path, args.mvd3)

        if args.instantiate:
            LOGGER.info("Preparing morphology output folder...")
            morph_writer = utils.MorphWriter(args.out_morph_dir, args.out_morph_ext)
            morph_writer.prepare(
                num_files=len(self.cells.positions),
                max_files_per_dir=args.max_files_per_dir,
                overwrite=args.overwrite
            )
        else:
            morph_writer = None

        np.random.seed(args.seed)

        LOGGER.info("Assigning CellCollection 'orientation' property...")
        rotations = None
        if args.rotations:
            rotations = utils.load_yaml(args.rotations)
            schema = utils.load_yaml(resource_path("data/schemas/rotations.yaml"))
            validate_config(rotations, schema=schema)

        atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)
        orientation_field = atlas.load_data("orientation", cls=OrientationField)
        assign_orientations(
            cells=self.cells,
            orientations=orientation_field.lookup(self.cells.positions),
            config=rotations,
        )

        LOGGER.info("Verifying morphology list(s)...")
        self._check_morph_lists(
            {'dend': args.morph, 'axon': args.morph_axon}, max_na_ratio=args.max_drop_ratio
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
          - dump CellCollection to MVD3
        """
        LOGGER.info("Assigning CellCollection 'morphology' property...")
        utils.assign_morphologies(self.cells, result)

        LOGGER.info("Export CellCollection...")
        utils.save_cells(self.cells, self.args.out_cells_path, mvd3_filepath=self.args.out_mvd3)


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

        self.cells = utils.load_cells(args.cells_path, args.mvd3)
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
        if 'scale' in rec:
            transform = rec['scale'] * np.identity(4)
            mt.transform(result, transform)
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
    utils.setup_logger()
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
        morph_list = utils.load_morphology_list(args.morph)
        if 'scale' in morph_list:
            raise RuntimeError("""
                Morphology list specifies scaling factors.
                It should be used with `--instantiate`.
            """)
        app = Master()
        app.setup(args)
        app.finalize(morph_list['morphology'])  # pylint: disable=unsubscriptable-object


if __name__ == '__main__':
    main()
