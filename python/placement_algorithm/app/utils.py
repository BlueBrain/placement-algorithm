"""
Miscellaneous utilities.
"""
import os
import random
import uuid

import numpy as np


def load_json(filepath):
    """ Load JSON file. """
    import ujson
    with open(filepath) as f:
        return ujson.load(f)


def random_rotation_y(n):
    """
    Random rotation around Y-axis.

    Args:
        n: number of rotation matrices to generate

    Returns:
        n x 3 x 3 NumPy array with rotation matrices.
    """
    # copied from `brainbuilder.cell_orientations` to avoid a heavy dependency
    # consider reusing `brainbuilder` methods if we need something more general
    # (like user-defined distributions for rotation angles)
    from voxcell.math_utils import angles_to_matrices
    angles = np.random.uniform(-np.pi, np.pi, size=n)
    return angles_to_matrices(angles, axis='y')


def multiply_matrices(A, B):
    """
    Vectorized matrix multiplication.

    Args:
        A: NumPy array of shape n x A x B
        B: NumPy array of shape n x B x C

    Returns:
        [np.dot(A[i], B[i]) for i in 0..n-1]
    """
    return np.einsum('...ij,...jk->...ik', A, B)


def get_layer_profile(xyz, atlas, layer_names):
    """ Get layer profile for given position. """
    result = {}
    result['y'] = atlas.load_data('[PH]y').lookup(xyz)
    for layer in layer_names:
        y0, y1 = atlas.load_data('[PH]%s' % layer).lookup(xyz)
        result['%s_0' % layer] = y0
        result['%s_1' % layer] = y1
    return result


def dump_morphology_list(morph_list, output_path):
    """ Dump morphology list to tab-separated file. """
    morph_list.to_csv(output_path, sep='\t', na_rep='N/A')


def load_morphology_list(filepath, check_gids=None):
    """ Read morphology list from tab-separated file. """
    import pandas as pd
    result = pd.read_csv(filepath, sep=r'\s+', index_col=0, na_filter=False)
    result['morphology'].replace({'N/A': None}, inplace=True)
    if check_gids is not None:
        if sorted(result.index) != sorted(check_gids):
            raise RuntimeError("Morphology list GIDs mismatch")
    return result


class MorphWriter(object):
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
        os.mkdir(dirpath)
        if depth <= 0:
            return
        for sub in range(256):
            MorphWriter._make_subdirs(os.path.join(dirpath, "%02x" % sub), depth - 1)

    def prepare(self, num_files, max_files_per_dir=None):
        """
        Prepare output directory.

          - ensure it either does not exist, or is empty
          - if it does not exist, create an empty one
        """
        self._dir_depth = MorphWriter._calc_dir_depth(
            num_files * len(self.file_ext), max_files_per_dir
        )
        if os.path.exists(self.output_dir):
            if os.listdir(self.output_dir):
                raise RuntimeError("Non-empty morphology output folder '%s'" % self.output_dir)
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
        morph_name, subdirs = self._generate_name(seed)
        for ext in self.file_ext:
            filepath = os.path.join(self.output_dir, subdirs, "%s.%s" % (morph_name, ext))
            morph.write(filepath)
        return morph_name
