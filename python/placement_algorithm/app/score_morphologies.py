#!/usr/bin/env python

"""
Show all scores for a given candidate position (i.e. m(e)type + layer profile).
"""
from __future__ import print_function

import sys
import argparse
import logging

import ujson

from placement_algorithm import algorithm, files


L = logging.getLogger('score-morphologies')


def _list_morphologies(morphdb, mtype, etype=None):
    # pylint: disable=unused-argument
    query = 'mtype == @mtype'
    if etype is not None:
        query += ' and etype == @etype'
    return morphdb.query(query)['morphology'].unique()


def main():
    """ Application entry point. """

    logging.basicConfig(level=logging.WARN)
    L.setLevel(logging.INFO)

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
        "--segment-type", help="Segment type to consider (if not specified, consider both)",
        choices=['axon', 'dendrite'],
        default=None,
    )
    args = parser.parse_args()

    all_rules = files.PlacementRules(args.rules)
    morphdb = files.parse_morphdb(args.morphdb)

    with open(args.annotations) as f:
        all_annotations = ujson.load(f)

    for line in sys.stdin:
        profile = ujson.loads(line)
        mtype, etype = profile['mtype'], profile.get('etype')

        morphologies = _list_morphologies(morphdb, mtype=mtype, etype=etype)
        if len(morphologies) < 1:
            raise RuntimeError("No morphologies found for %s" % profile)

        annotations = {
            m: all_annotations[m] for m in morphologies
        }

        rules, params = all_rules.bind(annotations, mtype=mtype)

        result = algorithm.score_morphologies(
            profile, rules, params, segment_type=args.segment_type
        )

        result.sort_values('total', ascending=False, inplace=True)
        result.index.name = 'morphology'
        result.rename(columns=lambda s: s.replace(' ', ''), inplace=True)
        result.to_csv(sys.stdout, sep='\t', float_format="%.3f", index=True)


if __name__ == '__main__':
    main()
