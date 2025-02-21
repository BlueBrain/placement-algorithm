#!/usr/bin/env python

"""
- choose morphologies using placement hints
- dump the list of chosen morphologies to TSV file
"""

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from voxcell.nexus.voxelbrain import Atlas

from placement_algorithm import files, algorithm
from placement_algorithm.app import utils
from placement_algorithm.app.mpi_app import MasterApp, WorkerApp
from placement_algorithm.logger import LOGGER


def _fetch_atlas_data(atlas, layer_names, memcache=False):
    """ Fetch '[PH]' datasets to disk; cache in memory if requested. """
    for dset in itertools.chain(['y'], layer_names):
        dset = f'[PH]{dset}'
        if memcache:
            atlas.load_data(dset, memcache=True)
        else:
            atlas.fetch_data(dset)


def _metype_columns(with_etype):
    result = ['layer', 'mtype']
    if with_etype:
        result.append('etype')
    return result


def _unique_values(df, columns):
    return set(
        df[columns].drop_duplicates().itertuples(index=False, name=None)
    )


def _check_has_metypes(morphdb, traits):
    key_columns = _metype_columns(with_etype=('etype' in morphdb))
    required = _unique_values(traits, key_columns)
    missing = required - _unique_values(morphdb, key_columns)
    if missing:
        raise RuntimeError(f"Missing m(e)types in (ext)neurondb.dat: [{sorted(missing)}]")


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
        from `morphdb` corresponding to `m(e)type`.
    """
    result = {}
    key_columns = _metype_columns(with_etype=('etype' in morphdb))
    mtype_idx = key_columns.index('mtype')
    for key, group in morphdb.groupby(key_columns):
        if not isinstance(key, tuple):
            key = (key,)
        mtype = key[mtype_idx]
        group_annotations = {
            m: annotations[m] for m in group['morphology'].unique()
            if m in annotations
        }
        result[key] = rules.bind(group_annotations, mtype)
    return result


class Master(MasterApp):
    """ MPI application master task. """
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
            "--segment-type", help="Segment type to consider (if not specified, consider both)",
            choices=['axon', 'dendrite'],
            default=None,
        )
        parser.add_argument(
            "--alpha",
            help="Use `score ** alpha` as morphology choice probability (default: %(default)s)",
            type=float,
            default=1.0
        )
        parser.add_argument(
            "--scales",
            type=float,
            nargs='+',
            help="Scale(s) to check",
            default=None
        )
        parser.add_argument(
            "--seed",
            help="Random number generator seed (default: %(default)s)",
            type=int,
            default=0
        )
        parser.add_argument(
            "-o", "--output", help="Path to output TSV file", required=True
        )
        parser.add_argument(
            "--no-mpi",
            help="Do not use MPI and run everything on a single core.",
            action='store_true',
        )
        parser.add_argument(
            "--scores-output-path",
            help="Directory path to which the scores for each cell are exported.",
            default=None,
        )
        parser.add_argument(
            "--bias-kind",
            help=(
                "Kind of bias used to penalize scores of rescaled morphologies "
                "(default: %(default)s)"
            ),
            choices=[algorithm.UNIFORM_BIAS, algorithm.LINEAR_BIAS, algorithm.GAUSSIAN_BIAS],
            default=algorithm.LINEAR_BIAS,
        )
        parser.add_argument(
            "--no-optional-scores",
            action="store_true",
            help="Trigger to ignore optional rules for morphology choice.",
        )

        return parser.parse_args()

    def setup(self, args):
        """
        Initialize master task.

          - load CellCollection
          - parse placement rules XML
          - parse MorphDB file
          - load and bind morphology annotations
          - prefetch atlas data
        """
        # pylint: disable=attribute-defined-outside-init

        LOGGER.info("Loading CellCollection...")
        self.cells = utils.load_cells(args.cells_path, args.mvd3)

        LOGGER.info("Loading placement rules...")
        rules = files.PlacementRules(args.rules)

        LOGGER.info("Loading MorphDB...")
        morphdb = files.parse_morphdb(args.morphdb)

        _check_has_metypes(morphdb, self.cells.properties)

        LOGGER.info("Loading and binding annotations...")
        annotations = _bind_annotations(
            utils.load_json(args.annotations), morphdb, rules
        )

        # Fetch required datasets from VoxelBrain if necessary,
        # so that when workers need them, they can get them directly from disk
        # without a risk of race condition for download.
        LOGGER.info("Fetching atlas data...")
        _fetch_atlas_data(
            Atlas.open(args.atlas, cache_dir=args.atlas_cache),
            layer_names=rules.layer_names
        )

        self.args = args

        return Worker(annotations, rules.layer_names, ('etype' in morphdb))

    @property
    def task_ids(self):
        """ Task IDs (= CellCollection IDs). """
        return self.cells.properties.index.values

    def finalize(self, result):
        """
        Finalize master task.

          - check result for N/A morphologies
          - calculate N/A ratio by mtype
          - dump morphology list to TSV file
        """
        if self.args.scales is None:
            result = pd.DataFrame({
                'morphology': pd.Series(result)
            })
        else:
            result = pd.DataFrame(result, index=['morphology', 'scale']).transpose()
        result.sort_index(inplace=True)

        utils.check_na_morphologies(result, mtypes=self.cells.properties['mtype'], threshold=None)
        utils.dump_morphology_list(result, self.args.output)


class Worker(WorkerApp):
    """ MPI application worker task. """
    def __init__(self, annotations, layer_names, with_etype):
        self.annotations = annotations
        self.layer_names = layer_names
        self.key_columns = _metype_columns(with_etype=with_etype)

    def setup(self, args):
        """
        Initialize worker.

          - load CellCollection
          - load atlas data into memory
        """
        # pylint: disable=attribute-defined-outside-init
        self.cells = utils.load_cells(args.cells_path, args.mvd3)
        self.atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)
        self.alpha = args.alpha
        self.scales = args.scales
        self.seed = args.seed
        self.segment_type = args.segment_type
        _fetch_atlas_data(self.atlas, self.layer_names, memcache=True)

        self.scores_output_path = args.scores_output_path
        self.bias_kind = args.bias_kind
        self._score_suffix_len = len(str(self.cells.properties.index.max()))
        self.with_optional_scores = not bool(args.no_optional_scores)

    def _get_profile(self, gid):
        """ Query layer profile for given GID. """
        return utils.get_layer_profile(
            self.cells.positions[gid],
            self.atlas,
            self.layer_names
        )

    def _get_annotations(self, gid):
        """ Get annotated morphologies matching given GID. """
        key = tuple(self.cells.properties.loc[gid, self.key_columns])
        return self.annotations[key]

    def __call__(self, gid):
        """
        Choose morphology for `gid` position using placement hints.

        Returns:
            Chosen morphology name (`None` if no matching morphology found).
        """
        seed = (self.seed + gid) % (1 << 32)
        np.random.seed(seed)
        profile = self._get_profile(gid)
        rules, params = self._get_annotations(gid)
        if self.scores_output_path is not None:
            score_folder = Path(self.scores_output_path)
            score_folder.mkdir(exist_ok=True)
            score_file = score_folder / f"scores_{gid:0{self._score_suffix_len}}.csv"
        else:
            score_file = None
        return algorithm.choose_morphology(
            profile, rules, params,
            alpha=self.alpha, scales=self.scales, segment_type=self.segment_type,
            scores_output_file=score_file, bias_kind=self.bias_kind,
            with_optional_scores=self.with_optional_scores
        )


def main():
    """ Application entry point. """
    utils.setup_logger()
    from placement_algorithm.app.mpi_app import run
    run(Master)


if __name__ == '__main__':
    main()
