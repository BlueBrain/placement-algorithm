#!/usr/bin/env python

import imp

from setuptools import setup, find_packages

VERSION = imp.load_source("", "placement_algorithm/version.py").__version__

APP_EXTRAS = [
    'morphio>=2.0.5',
    'morph-tool>=0.2.10',
    'neuroc',
    'neurom>=2.0.1',
    'tqdm>=4.0',
    'voxcell>=2.7',
    'dask[distributed,bag]>=2.15.0',
]

SYNTHESIS_EXTRAS = [
    'region-grower>=0.1.11,<0.2',
    'tns',
]

MPI_EXTRAS = [
    'mpi4py>=3.0.3',
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
    ],
    extras_require={
        'app': APP_EXTRAS,
        'synthesis': SYNTHESIS_EXTRAS,
        'mpi': MPI_EXTRAS,
        'all': APP_EXTRAS + SYNTHESIS_EXTRAS + MPI_EXTRAS
    },
    packages=find_packages(),
    python_requires='>=3.6',
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
