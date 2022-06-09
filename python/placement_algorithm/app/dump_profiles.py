#!/usr/bin/env python

"""
Dump layer profile for GID(s) of interest.
"""

from __future__ import print_function

import argparse
import itertools
from collections import OrderedDict

import json

from voxcell.nexus.voxelbrain import Atlas

from placement_algorithm.app.utils import get_layer_profile, load_cells


def main():
    """ Application entry point. """
    parser = argparse.ArgumentParser(
        description="Dump layer profile(s)"
    )
    parser.add_argument(
        "--mvd3", help="Deprecated! Path to input MVD3 file. Use --cells-path instead."
    )
    parser.add_argument(
        "--cells-path", help="Path to a file storing cells collection"
    )
    parser.add_argument(
        "--atlas", help="Atlas URL", required=True
    )
    parser.add_argument(
        "--atlas-cache", help="Atlas cache folder", default=None
    )
    parser.add_argument(
        "--layer-names", help="Comma-separated layer names", required=True
    )
    parser.add_argument(
        "--gids", type=int, nargs='+', help="GID(s) to check (zero-based)", default=None
    )
    args = parser.parse_args()

    cells = load_cells(args.cells_path, args.mvd3)
    atlas = Atlas.open(args.atlas, cache_dir=args.atlas_cache)

    if args.gids is None:
        gids = cells.properties.index
    else:
        gids = args.gids

    layer_names = args.layer_names.split(',')
    for dset in itertools.chain(['y'], layer_names):
        atlas.load_data(f'[PH]{dset}', memcache=True)

    for gid in gids:
        profile = get_layer_profile(cells.positions[gid], atlas, layer_names)
        profile = OrderedDict([
            (k, float(v))
            for k, v in sorted(profile.items())
        ])
        profile['mtype'] = cells.properties['mtype'][gid]
        profile['etype'] = cells.properties['etype'][gid]
        profile['gid'] = gid
        if 'layer' in cells.properties:
            profile['layer'] = str(cells.properties['layer'][gid])

        print(json.dumps(profile))


if __name__ == '__main__':
    main()
