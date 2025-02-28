#!/usr/bin/env python
import importlib.util

from setuptools import setup, find_packages

spec = importlib.util.spec_from_file_location(
    "placement_algorithm.version",
    "placement_algorithm/version.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
VERSION = module.__version__

APP_EXTRAS = [
    'morphio>=3.0',
    'morph-tool>=2.9.0,<3.0',
    'tqdm>=4.0',
    'voxcell>=2.7,<4.0',
    'dask[distributed,bag]>=2.15.0',
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
    long_description="Morphology placement algorithm",
    long_description_content_type="text/plain",
    url="https://bbpteam.epfl.ch/project/issues/projects/NSETM/issues",
    download_url="https://bbpteam.epfl.ch/repository/devpi/+search?query=name%3Aplacement-algorithm",
    license="BBP-internal-confidential",
    install_requires=[
        'jsonschema>=3.2.0',
        'lxml>=4.0',
        'numpy>=1.8',
        'pandas>0.19',
        'scipy>=1.2.0',
        'pyyaml>=5.3.1',
    ],
    extras_require={
        'app': APP_EXTRAS,
        'mpi': MPI_EXTRAS,
        'all': APP_EXTRAS + MPI_EXTRAS
    },
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.7',
    entry_points={
      'console_scripts': [
          'assign-morphologies=placement_algorithm.app.assign_morphologies:main',
          'choose-morphologies=placement_algorithm.app.choose_morphologies:main',
          'compact-annotations=placement_algorithm.app.compact_annotations:main',
          'dump-profiles=placement_algorithm.app.dump_profiles:main',
          'score-morphologies=placement_algorithm.app.score_morphologies:main',
      ]
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
