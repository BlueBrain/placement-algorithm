import os
import shutil
import tempfile

import mock
import nose.tools as nt
import numpy as np
import numpy.testing as npt
import pandas as pd
from pandas.testing import assert_frame_equal

from contextlib import contextmanager
from mock import patch, Mock

from voxcell import CellCollection

import placement_algorithm.app.utils as test_module


def test_random_rotation_y_1():
    np.random.seed(42)
    expected = [
        [
            [ 0.7050606, 0., -0.709147 ],
            [ 0.       , 1.,  0.       ],
            [ 0.709147 , 0.,  0.7050606],
        ]
    ]
    npt.assert_almost_equal(
        test_module.random_rotation_y(1),
        expected
    )


def test_random_rotation_y_2():
    np.random.seed(42)
    expected = [
        [
            [ 0.7050606, 0., -0.709147 ],
            [ 0.       , 1.,  0.       ],
            [ 0.709147 , 0.,  0.7050606],
        ],
        [
            [-0.9524338, 0.,  0.3047454],
            [ 0.       , 1.,  0.       ],
            [-0.3047454, 0., -0.9524338],
        ],
    ]
    npt.assert_almost_equal(
        test_module.random_rotation_y(2),
        expected
    )


def test_multiply_matrices():
    np.random.seed(42)
    As = np.random.random((2, 3, 3))
    Bs = np.random.random((2, 3, 3))
    expected = [np.dot(A, B) for A, B in zip(As, Bs)]
    npt.assert_almost_equal(
        test_module.multiply_matrices(As, Bs),
        expected
    )


def test_get_layer_profile():
    xyz = [1., 2., 3.]
    layers = ['B', 'A']
    atlas = Mock()
    atlas.load_data.side_effect = [
        Mock(**{'lookup.return_value': 'y_value'}),
        Mock(**{'lookup.return_value': ('B0_value', 'B1_value')}),
        Mock(**{'lookup.return_value': ('A0_value', 'A1_value')}),
    ]
    expected = {
        'y': 'y_value',
        'A_0': 'A0_value',
        'A_1': 'A1_value',
        'B_0': 'B0_value',
        'B_1': 'B1_value',
    }
    nt.assert_equal(
        test_module.get_layer_profile(xyz, atlas, layers),
        expected
    )
    atlas.assert_has_calls([
        mock.call.load_data('[PH]y'),
        mock.call.load_data('[PH]B'),
        mock.call.load_data('[PH]A'),
    ])


@contextmanager
def tempcwd():
    cwd = os.getcwd()
    dirname = tempfile.mkdtemp()
    os.chdir(dirname)
    try:
        yield dirname
    finally:
        os.chdir(cwd)
        shutil.rmtree(dirname)


def test_dump_morphology_list():
    original = pd.DataFrame({
        'morphology': ['morph-A', None, 'morph-C'],
        'scale': [1., np.nan, 2.]
    })
    expected = pd.DataFrame({
        'morphology': ['morph-A', 'N/A', 'morph-C'],
        'scale': ['1.0', 'N/A', '2.0'],
    }, index=['0', '1', '2'])
    with tempcwd():
        test_module.dump_morphology_list(original, 'morph_list.tsv')
        loaded = pd.read_csv('morph_list.tsv', sep=r'\s+', dtype=str, na_filter=False)
    assert_frame_equal(loaded, expected, check_like=True)


def test_dump_load_morphology_list_1():
    original = pd.DataFrame({
        'morphology': ['morph-A', None, 'morph-C'],
        'scale': [1.0, None, 2.0],
    })
    with tempcwd():
        test_module.dump_morphology_list(original, 'morph_list.tsv')
        loaded = test_module.load_morphology_list('morph_list.tsv')
    assert_frame_equal(original, loaded, check_like=True)


def test_dump_load_morphology_list_2():
    original = pd.DataFrame({
        'morphology': ['morph-A', None, 'morph-C'],
    }, index=[2, 1, 0])
    with tempcwd():
        test_module.dump_morphology_list(original, 'morph_list.tsv')
        loaded = test_module.load_morphology_list('morph_list.tsv', check_gids=[0, 2, 1])
    assert_frame_equal(loaded, original, check_like=True)


def test_dump_load_morphology_list_3():
    original = pd.DataFrame({
        'morphology': ['morph-A', None, 'morph-C'],
    })
    with tempcwd():
        test_module.dump_morphology_list(original, 'morph_list.tsv')
        nt.assert_raises(
            RuntimeError,  # GIDs mismatch
            test_module.load_morphology_list,
            'morph_list.tsv', check_gids=range(5)
        )


@patch(__name__ + '.test_module.LOGGER')
def test_check_na_morphologies(logger):
    morph_list = pd.DataFrame({
        'morphology': ['morph-A', None, 'morph-C'],
    })
    mtypes = pd.Series([
        'mtype-A', 'mtype-A', 'mtype-C'
    ])
    nt.assert_raises(
        RuntimeError,  # Max N/A ratio exceeded
        test_module.check_na_morphologies,
        morph_list, mtypes, threshold=0.1
    )
    logger.warning.assert_called_with(mock.ANY, 1)
    logger.info.assert_called_with(
        mock.ANY,
        '         N/A  out of  ratio, %\n'
        'mtype-A    1       2      50.0'
    )


def test_assign_morphologies():
    cells = CellCollection()
    cells.properties = pd.DataFrame({
        'name': ['A', 'B', 'C', 'D']
    })
    morphologies = {
        2: 'morph-Y',
        1: 'morph-X',
        3: 'morph-Y',
        0: None,  # to be dropped
    }
    test_module.assign_morphologies(cells, morphologies)
    assert_frame_equal(
        cells.properties,
        pd.DataFrame({
            'name': ['B', 'C', 'D'],
            'morphology': ['morph-X', 'morph-Y', 'morph-Y']
        }),
        check_like=True
    )


class TestMorphWriter(object):
    def setup(self):
        self.test_obj = test_module.MorphWriter('/root', ['asc', 'swc'])

    def test_calc_dir_depth(self):
        nt.assert_is_none(
            test_module.MorphWriter._calc_dir_depth(2 ** 20)
        )
        nt.assert_equal(
            test_module.MorphWriter._calc_dir_depth(2 ** 20, max_files_per_dir=256),
            2
        )
        nt.assert_raises(
            RuntimeError,  # too few files per folder
            test_module.MorphWriter._calc_dir_depth,
            2 ** 20, max_files_per_dir=100
        )
        nt.assert_raises(
            RuntimeError,  # too many intermediate folders
            test_module.MorphWriter._calc_dir_depth,
            2 ** 40, max_files_per_dir=256
        )

    @patch('os.path.exists', return_value=False)
    @patch('os.mkdir')
    def test_make_subdirs(self, os_mkdir, _):
        test_module.MorphWriter._make_subdirs('/root', depth=1)
        nt.assert_equal(os_mkdir.call_count, 257)
        os_mkdir.assert_has_calls([
            mock.call('/root'),
            mock.call('/root/00'),
            mock.call('/root/01'),
        ])
        os_mkdir.assert_has_calls([
            mock.call('/root/fe'),
            mock.call('/root/ff'),
        ])

    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_prepare_1(self, os_makedirs, _):
        self.test_obj.prepare(2 ** 10)
        nt.assert_is_none(self.test_obj._dir_depth)
        os_makedirs.assert_called_once_with('/root')

    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=[])
    def test_prepare_2(self, _, _2):
        self.test_obj.prepare(2 ** 10)
        nt.assert_is_none(self.test_obj._dir_depth)

    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=['a'])
    def test_prepare_3(self, _, _2):
        nt.assert_raises(
            RuntimeError,  # non-empty morphology output folder
            self.test_obj.prepare,
            2 ** 10
        )

    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=['a'])
    def test_prepare_4(self, _, _2):
        self.test_obj.prepare(2 ** 10, overwrite=True)
        nt.assert_is_none(self.test_obj._dir_depth)

    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=[])
    @patch(test_module.__name__ + '.MorphWriter._calc_dir_depth')
    @patch(test_module.__name__ + '.MorphWriter._make_subdirs')
    def test_prepare_5(self, make_subdirs, calc_dir_depth, _, _2):
        calc_dir_depth.return_value = 3
        self.test_obj.prepare(2 ** 10, max_files_per_dir=42)
        calc_dir_depth.assert_called_once_with(2 ** 11, 42)
        make_subdirs.assert_called_once_with('/root/hashed', 3)

    def test_generate_name_1(self):
        self.test_obj._dir_depth = None
        nt.assert_equal(
            self.test_obj._generate_name(42),
            ('bdd640fb06671ad11c80317fa3b1799d', '')
        )

    def test_generate_name_2(self):
        self.test_obj._dir_depth = 2
        nt.assert_equal(
            self.test_obj._generate_name(42),
            ('bdd640fb06671ad11c80317fa3b1799d', 'hashed/bd/d6')
        )

    @patch('morphio.mut.Morphology')
    def test_call(self, morph_cls):
        import morphio
        self.test_obj._dir_depth = 2
        self.test_obj('morph-obj', 42)
        morph_cls.assert_has_calls([
            mock.call('morph-obj', options=morphio.Option.nrn_order),
            mock.call().write('/root/hashed/bd/d6/bdd640fb06671ad11c80317fa3b1799d.asc'),
            mock.call().write('/root/hashed/bd/d6/bdd640fb06671ad11c80317fa3b1799d.swc'),
        ])
