#!/usr/bin/env python

"""
Show all scores for a given candidate position (i.e. m(e)type + layer profile).
"""
from __future__ import print_function

import sys
import argparse
import json

import pandas as pd

from placement_algorithm import algorithm, files
from placement_algorithm.app import utils


def _list_morphologies(morphdb, mtype, etype=None, layer=None):
    # pylint: disable=unused-argument
    query = 'mtype == @mtype'
    if ('etype' in morphdb) and (etype is not None):
        query += ' and etype == @etype'
    if ('layer' in morphdb) and (layer is not None):
        query += ' and layer == @layer'
    return morphdb.query(query)['morphology'].unique()


def _score_morphologies(profile, rules, params, scales=None, segment_type=None):
    if scales is None:
        result = algorithm.score_morphologies(
            profile, rules, params, segment_type=segment_type
        )
        result.index.name = 'morphology'
    else:
        result = {}
        for scale in scales:
            result[scale] = algorithm.score_morphologies(
                profile, rules, params, scale=scale, segment_type=segment_type
            )
        result = pd.concat(result, names=('scale', 'morphology')).swaplevel()
    return result


def main():
    """ Application entry point. """
    utils.setup_logger()

    parser = argparse.ArgumentParser(
        description="Choose morphology for a given layer profile."
    )
    parser.add_argument(
        "--morphdb", help="Path to MorphDB file", required=True
    )
    parser.add_argument(
        "--annotations", help="Path to JSON with morphology annotations", required=True
    )
    parser.add_argument(
        "--rules", help="Path to placement rules file", required=True,
    )
    parser.add_argument(
        "--scales",
        type=float,
        nargs='+',
        help="Scale(s) to check",
        default=None
    )
    parser.add_argument(
        "--segment-type", help="Segment type to consider (if not specified, consider both)",
        choices=['axon', 'dendrite'],
        default=None,
    )
    args = parser.parse_args()

    all_rules = files.PlacementRules(args.rules)
    morphdb = files.parse_morphdb(args.morphdb)

    all_annotations = utils.load_json(args.annotations)

    for line in sys.stdin:
        profile = json.loads(line)
        mtype, etype, layer = profile['mtype'], profile.get('etype'), profile.get('layer')

        morphologies = _list_morphologies(morphdb, mtype=mtype, etype=etype, layer=layer)
        if len(morphologies) < 1:
            raise RuntimeError(f"No morphologies found for {profile}")

        annotations = {
            m: all_annotations[m] for m in morphologies
        }

        rules, params = all_rules.bind(annotations, mtype=mtype)

        result = _score_morphologies(
            profile, rules, params, scales=args.scales, segment_type=args.segment_type
        )

        result.sort_values('total', ascending=False, inplace=True)
        result.rename(columns=lambda s: s.replace(' ', ''), inplace=True)
        result.to_csv(sys.stdout, sep='\t', float_format="%.3f", na_rep='NaN', index=True)


if __name__ == '__main__':
    main()
