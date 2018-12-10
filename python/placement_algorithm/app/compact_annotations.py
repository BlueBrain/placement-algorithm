#!/usr/bin/env python

"""
Compact folder with morphology annotations as XML files into single JSON file.
"""

import argparse
import glob
import os

import ujson

from tqdm import tqdm

from placement_algorithm import files


def _collect_annotations(annotation_dir):
    result = {}
    for filepath in tqdm(glob.glob(os.path.join(annotation_dir, "*.xml"))):
        morph, _ = os.path.splitext(os.path.basename(filepath))
        result[morph] = files.parse_annotations(filepath)
    return result


def main():
    """ Application entry point. """
    parser = argparse.ArgumentParser(
        description="Compact folder with morphology annotations into single JSON file."
    )
    parser.add_argument(
        "annotation_dir", help="Path to annotations folder"
    )
    parser.add_argument(
        "-o", "--output", help="Path to output JSON file", required=True
    )
    args = parser.parse_args()

    annotations = _collect_annotations(args.annotation_dir)

    with open(args.output, 'w') as f:
        ujson.dump(annotations, f, indent=2)


if __name__ == '__main__':
    main()
