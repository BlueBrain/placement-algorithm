#!/usr/bin/env python

import imp
import sys

from setuptools import setup, find_packages

if sys.version_info < (2, 7):
    sys.exit("Sorry, Python < 2.7 is not supported")

VERSION = imp.load_source("", "placement_algorithm/version.py").__version__

setup(
    name="placement-algorithm",
    author="BlueBrain NSE",
    author_email="bbp-ou-nse@groupes.epfl.ch",
    version=VERSION,
    description="Morphology placement algorithm",
    url="https://bbpteam.epfl.ch/project/issues/projects/NSETM/issues",
    download_url="ssh://bbpcode.epfl.ch/building/placementAlgorithm",
    license="BBP-internal-confidential",
    install_requires=[
        'lxml>=4.0',
        'numpy>=1.8',
        'pandas>0.19',
        'six>=1.0',
        'tqdm>=4.0',
        'ujson>=1.0',
    ],
    packages=find_packages(),
    entry_points={
      'console_scripts': [
          'compact-annotations=placement_algorithm.app.compact_annotations:main',
          'score-morphologies=placement_algorithm.app.score_morphologies:main',
      ]
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)
