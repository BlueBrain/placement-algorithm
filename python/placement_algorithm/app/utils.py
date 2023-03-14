"""
Miscellaneous utilities.
"""
import json
import os
import logging
import random
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

import morphio
import yaml
from voxcell import CellCollection

from placement_algorithm.logger import LOGGER


def setup_logger():
    """Setup application logger."""
    logging.basicConfig(
        format="%(asctime)s;%(levelname)s;%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=logging.ERROR
    )
    LOGGER.setLevel(logging.INFO)


def load_json(filepath):
    """Load JSON file."""
    with open(filepath, mode="r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(filepath):
    """Load YAML file."""
    with open(filepath, mode="r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_cells(filepath, mvd3_filepath=None):
    """Load CellCollection from file.

    Args:
        filepath (str): cells file
        mvd3_filepath (str): MVD3 cells file. Temporary for backward compatibility.

    Returns:
        CellCollection: cells
    """
    if mvd3_filepath is not None:
        LOGGER.warning('--mvd3 option is deprecated. Use --cells_path instead.')
        return CellCollection.load_mvd3(mvd3_filepath)
    if filepath is None:
        raise ValueError('`--cells-path` option is required')
    return CellCollection.load(filepath)


def save_cells(cells, filepath, mvd3_filepath=None):
    """Save CellCollection to file.

    Args:
        cells (CellCollection): cells to be saved
        filepath (str): cells file
        mvd3_filepath (str): MVD3 cells file. Temporary for backward compatibility.
    """
    if mvd3_filepath:
        LOGGER.warning('--out-mvd3 option is deprecated. Use --out-cells-path instead.')
        cells.save_mvd3(mvd3_filepath)
    elif filepath is None:
        raise ValueError('`--out-cells-path` option is required')
    else:
        cells.save(filepath)


def get_layer_profile(xyz, atlas, layer_names):
    """ Get layer profile for given position. """
    result = {}
    result['y'] = atlas.load_data('[PH]y').lookup(xyz)
    for layer in layer_names:
        y0, y1 = atlas.load_data(f'[PH]{layer}').lookup(xyz)
        result[f'{layer}_0'] = y0
        result[f'{layer}_1'] = y1
    return result


def dump_morphology_list(morph_list, output_path):
    """ Dump morphology list to tab-separated file. """
    morph_list.to_csv(output_path, sep='\t', na_rep='N/A')


def load_morphology_list(filepath, check_gids=None):
    """ Read morphology list from tab-separated file. """
    result = pd.read_csv(
        filepath, sep=r'\s+', index_col=0, dtype={'morphology': object, 'scale': float}
    )
    result['morphology'].replace({np.nan: None}, inplace=True)
    if check_gids is not None:
        if sorted(result.index) != sorted(check_gids):
            raise RuntimeError("Morphology list GIDs mismatch")
    return result


def _failure_ratio_by_mtype(mtypes, na_mask):
    """ Calculate ratio of N/A occurences per mtype. """
    failed = mtypes[na_mask].value_counts()
    overall = mtypes.value_counts()
    result = pd.DataFrame({
        'N/A': failed,
        'out of': overall,
    }).dropna().astype(int)
    result['ratio, %'] = 100.0 * result['N/A'] / result['out of']
    result.sort_values('ratio, %', ascending=False, inplace=True)
    return result


def check_na_morphologies(morph_list, mtypes, threshold=None):
    """ Check `N/A` ratio per mtype. """
    na_mask = morph_list.isnull().any(axis=1)
    if na_mask.any():
        stats = _failure_ratio_by_mtype(mtypes, na_mask)
        LOGGER.warning(
            "N/A morphologies for %d position(s)", np.count_nonzero(na_mask)
        )
        LOGGER.info(
            "N/A ratio by mtypes:\n%s", stats.to_string(float_format="%.1f")
        )
        if threshold is not None:
            exceeded = 0.01 * stats['ratio, %'] > threshold
            if exceeded.any():
                ratio = 100.0 * threshold
                failed_mtypes = ", ".join(exceeded[exceeded].index)
                raise RuntimeError(
                    f"Max N/A ratio ({ratio:.1f}%) exceeded for mtype(s): {failed_mtypes}"
                )


class MorphWriter:
    """ Helper class for writing morphologies. """
    def __init__(self, output_dir, file_ext):
        self.output_dir = os.path.realpath(output_dir)
        self.file_ext = file_ext
        self._dir_depth = None

    @staticmethod
    def _calc_dir_depth(num_files, max_files_per_dir=None):
        """ Directory depth required to have no more than given number of files per folder. """
        if (max_files_per_dir is None) or (num_files < max_files_per_dir):
            return None
        if max_files_per_dir < 256:
            raise RuntimeError("""
                Less than 256 files per folder is too restrictive.
            """)
        result, capacity = 0, max_files_per_dir
        while capacity < num_files:
            result += 1
            capacity *= 256
        if result > 3:
            raise RuntimeError("""
                More than three intermediate folders is a bit too much.
            """)
        return result

    @staticmethod
    def _make_subdirs(dirpath, depth):
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)
        if depth <= 0:
            return
        for sub in range(256):
            MorphWriter._make_subdirs(os.path.join(dirpath, f"{sub:02x}"), depth - 1)

    def prepare(self, num_files, max_files_per_dir=None, overwrite=False):
        """
        Prepare output directory.

          - ensure it either does not exist, or is empty
          - if it does not exist, create an empty one
        """
        self._dir_depth = MorphWriter._calc_dir_depth(
            num_files * len(self.file_ext), max_files_per_dir
        )
        if os.path.exists(self.output_dir):
            if not overwrite and os.listdir(self.output_dir):
                raise RuntimeError(f"Non-empty morphology output folder '{self.output_dir}'")
        else:
            os.makedirs(self.output_dir)
        if self._dir_depth is not None:
            MorphWriter._make_subdirs(os.path.join(self.output_dir, 'hashed'), self._dir_depth)

    def _generate_name(self, seed):
        morph_name = uuid.UUID(int=random.Random(seed).getrandbits(128)).hex
        if self._dir_depth is None:
            subdirs = ''
        else:
            subdirs = 'hashed'
            assert len(morph_name) >= 2 * self._dir_depth
            for k in range(self._dir_depth):
                sub = morph_name[2 * k: 2 * k + 2]
                subdirs = os.path.join(subdirs, sub)
        return morph_name, subdirs

    def __call__(self, morph, seed):
        # TODO: pass nrn_order option directly to .write()
        morph = morphio.mut.Morphology(  # pylint: disable=no-member
            morph, options=morphio.Option.nrn_order
        )
        morph_name, subdirs = self._generate_name(seed)

        full_stem = Path(subdirs, morph_name)

        for ext in self.file_ext:
            morph.write(Path(self.output_dir, full_stem.with_suffix('.' + ext)))
        return str(full_stem)


def assign_morphologies(cells, morphologies):
    """
    Assign morphologies to CellCollection.

    Args:
        cells: CellCollection to be augmented
        morphologies: dictionary {gid -> morphology_name}

    No return value; `cells` is input/output argument.
    """
    cells.properties['morphology'] = pd.Series(morphologies)
    na_mask = cells.properties['morphology'].isnull()
    if na_mask.any():
        LOGGER.info(
            "Dropping %d cells with no morphologies assigned; reindexing",
            np.count_nonzero(na_mask)
        )
        cells.remove_unassigned_cells()
