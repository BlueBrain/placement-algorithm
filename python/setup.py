#!/usr/bin/env python

import imp
import sys

from setuptools import setup, find_packages

if sys.version_info < (2, 7):
    sys.exit("Sorry, Python < 2.7 is not supported")

VERSION = imp.load_source("", "placement_algorithm/version.py").__version__

APP_EXTRAS = [
    'morphio>=2.0',
    'morph-tool>=0.1',
    'tqdm>=4.0',
    'voxcell>=2.5',
]

SYNTHESIS_EXTRAS = [
    'region-grower',
    'tns',
]

MPI_EXTRAS = [
    'mpi4py>=2.0,<3.0',
]

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
    ],
    extras_require={
        'app': APP_EXTRAS,
        'synthesis': SYNTHESIS_EXTRAS,
        'mpi': MPI_EXTRAS,
        'all': APP_EXTRAS + SYNTHESIS_EXTRAS + MPI_EXTRAS
    },
    packages=find_packages(),
    entry_points={
      'console_scripts': [
          'assign-morphologies=placement_algorithm.app.assign_morphologies:main',
          'choose-morphologies=placement_algorithm.app.choose_morphologies:main',
          'compact-annotations=placement_algorithm.app.compact_annotations:main',
          'dump-profiles=placement_algorithm.app.dump_profiles:main',
          'score-morphologies=placement_algorithm.app.score_morphologies:main',
          'synthesize-morphologies=placement_algorithm.app.synthesize_morphologies:main',
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
