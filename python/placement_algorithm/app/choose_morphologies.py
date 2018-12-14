#!/usr/bin/env python

"""
- choose morphologies using placement hints
- dump the list of chosen morphologies to TSV file
"""

import argparse
import itertools
import logging

import numpy as np
import pandas as pd

from voxcell import CellCollection
from voxcell.nexus.voxelbrain import Atlas

from placement_algorithm import files, algorithm
from placement_algorithm.app import utils
from placement_algorithm.app.mpi_app import MasterApp, WorkerApp


LOGGER = logging.getLogger('choose-morphologies')


def _fetch_atlas_data(atlas, layer_names, memcache=False):
    """ Fetch '[PH]' datasets to disk; cache in memory if requested. """
    for dset in itertools.chain(['y'], layer_names):
        dset = '[PH]%s' % dset
        if memcache:
            atlas.load_data(dset, memcache=True)
        else:
            atlas.fetch_data(dset)


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
    if 'etype' in morphdb:
        key_columns = ['mtype', 'etype']
    else:
        key_columns = ['mtype']
    for key, group in morphdb.groupby(key_columns):
        mtype = key[0]
        mtype_annotations = {
            m: annotations[m] for m in group['morphology'].unique()
        }
        result[key] = rules.bind(mtype_annotations, mtype)
    return result


def _failure_ratio_by_mtype(mtypes, na_mask):
    """ Calculate ratio of N/A occurences per mtype. """
    failed = mtypes[na_mask].value_counts()
    overall = mtypes.value_counts()
    result = pd.DataFrame({
        'failed': failed,
        'out of': overall,
    }).dropna().astype(int)
    result['ratio, %'] = 100.0 * result['failed'] / result['out of']
    result.sort_values('ratio, %', ascending=False, inplace=True)
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
            "--seed",
            help="Random number generator seed (default: %(default)s)",
            type=int,
            default=0
        )
        parser.add_argument(
            "--allow-na",
            help="Allow positions with no morphologies assigned (default: %(default)s)",
            action="store_true"
        )
        parser.add_argument(
            "-o", "--output", help="Path to output TSV file", required=True
        )
        return parser.parse_args()

    @property
    def logger(self):
        """ Application logger. """
        return LOGGER

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
        logging.basicConfig(level=logging.ERROR)
        LOGGER.setLevel(logging.INFO)

        LOGGER.info("Loading CellCollection...")
        self.cells = CellCollection.load_mvd3(args.mvd3)

        LOGGER.info("Loading placement rules...")
        rules = files.PlacementRules(args.rules)

        LOGGER.info("Loading MorphDB...")
        morphdb = files.parse_morphdb(args.morphdb)

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
        result = pd.DataFrame({
            'morphology': pd.Series(result)
        })
        na_mask = result.isnull().any(axis=1)
        if na_mask.any():
            stats = _failure_ratio_by_mtype(self.cells.properties['mtype'], na_mask)
            LOGGER.warn(
                "Failed to choose morphologies for %d position(s)", np.count_nonzero(na_mask)
            )
            LOGGER.info(
                "Failure ratio by mtypes:\n%s", stats.to_string(float_format="%.1f")
            )
            if not self.args.allow_na:
                raise RuntimeError("""
                    Failed to choose morphologies for some positions.
                    Please re-run with `--allow-na` if it is acceptable.
                """)
        utils.dump_morphology_list(result, self.args.output)


class Worker(WorkerApp):
    """ MPI application worker task. """
    def __init__(self, annotations, layer_names, with_etype):
        self.annotations = annotations
        self.layer_names = layer_names
        self.with_etype = with_etype

    def setup(self, args):
        """
        Initialize worker.

          - load CellCollection
          - load atlas data into memory
        """
        # pylint: disable=attribute-defined-outside-init
        self.cells = CellCollection.load_mvd3(args.mvd3)
        self.atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)
        self.alpha = args.alpha
        self.seed = args.seed
        self.segment_type = args.segment_type
        _fetch_atlas_data(self.atlas, self.layer_names, memcache=True)

    def _get_profile(self, gid):
        """ Query layer profile for given GID. """
        xyz = self.cells.positions[gid]
        result = {}
        result['y'] = self.atlas.load_data('[PH]y').lookup(xyz)
        for layer in self.layer_names:
            y0, y1 = self.atlas.load_data('[PH]%s' % layer).lookup(xyz)
            result['%s_0' % layer] = y0
            result['%s_1' % layer] = y1
        return result

    def _get_annotations(self, gid):
        """ Get annotated morphologies matching given GID. """
        traits = self.cells.properties.loc[gid]
        if self.with_etype:
            key = (traits['mtype'], traits['etype'])
        else:
            key = traits['mtype']
        return self.annotations[key]

    def __call__(self, gid):
        """
        Choose morphology for `gid` position using placement hints.

        Returns:
            Chosen morphology name (`None` if no matching morphology found).
        """
        seed = hash((self.seed, gid)) % (1 << 32)
        np.random.seed(seed)
        profile = self._get_profile(gid)
        rules, params = self._get_annotations(gid)
        return algorithm.choose_morphology(
            profile, rules, params, alpha=self.alpha, segment_type=self.segment_type
        )


def main():
    """ Application entry point. """
    from placement_algorithm.app.mpi_app import run
    run(Master)


if __name__ == '__main__':
    main()
