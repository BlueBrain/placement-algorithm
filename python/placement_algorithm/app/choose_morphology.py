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


L = logging.getLogger('choose-morphology')


def _list_morphologies(morphdb, mtype, etype=None):
    # pylint: disable=unused-argument
    query = 'mtype == @mtype'
    if etype is not None:
        query += ' and etype == @etype'
    return morphdb.query(query)['morphology'].unique()


def main():
    """ Application entry point. """
    # pylint: disable=too-many-locals

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

        result, scores = algorithm.choose_morphology(
            profile, rules, params, alpha=args.alpha, seed=args.seed, return_scores=True
        )

        print("Result: %s (score=%.3f)" % (result, scores.loc[result, 'total']))

        print("Scores:")
        scores.sort_values('total', ascending=False, inplace=True)
        scores.index.name = 'morphology'
        scores.rename(columns=lambda s: s.replace(' ', ''), inplace=True)
        scores.to_csv(sys.stdout, sep='\t', float_format="%.3f", index=True)


if __name__ == '__main__':
    main()
