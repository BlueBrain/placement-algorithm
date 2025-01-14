import os
import shutil
import tempfile
from pathlib import Path

import unittest.mock as mock
import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from contextlib import contextmanager
from unittest.mock import patch, Mock

from voxcell import CellCollection

import placement_algorithm.app.utils as test_module


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
    assert (
        test_module.get_layer_profile(xyz, atlas, layers) ==
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
        with pytest.raises(RuntimeError, match="Morphology list GIDs mismatch"):
            test_module.load_morphology_list('morph_list.tsv', check_gids=range(5))


@patch(__name__ + '.test_module.LOGGER')
def test_check_na_morphologies(logger):
    morph_list = pd.DataFrame({
        'morphology': ['morph-A', None, 'morph-C'],
    })
    mtypes = pd.Series([
        'mtype-A', 'mtype-A', 'mtype-C'
    ])
    with pytest.raises(RuntimeError, match="Max N/A ratio .* exceeded for mtype"):
        test_module.check_na_morphologies(morph_list, mtypes, threshold=0.1)
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


@patch('voxcell.CellCollection.load')
@patch('voxcell.CellCollection.load_mvd3')
def test_load_cells(load_mvd3_mock, load_mock):
    test_module.load_cells('cells_path')
    load_mock.assert_called_once_with('cells_path')
    load_mvd3_mock.assert_not_called()


@patch('voxcell.CellCollection.load')
@patch('voxcell.CellCollection.load_mvd3')
def test_load_cells_mvd3(load_mvd3_mock, load_mock):
    test_module.load_cells('cells_path', 'mvd3_path')
    load_mvd3_mock.assert_called_once_with('mvd3_path')
    load_mock.assert_not_called()


class TestMorphWriter:
    def setup(self):
        self.test_obj = test_module.MorphWriter('/root', ['asc', 'swc'])

    def test_calc_dir_depth(self):
        assert test_module.MorphWriter._calc_dir_depth(2 ** 20) is None
        assert test_module.MorphWriter._calc_dir_depth(2 ** 20, max_files_per_dir=256) == 2
        with pytest.raises(
                RuntimeError, match="Less than 256 files per folder is too restrictive."
        ):
            test_module.MorphWriter._calc_dir_depth(2 ** 20, max_files_per_dir=100)
        with pytest.raises(
                RuntimeError, match="More than three intermediate folders is a bit too much."
        ):
            test_module.MorphWriter._calc_dir_depth(2 ** 40, max_files_per_dir=256)

    @patch('os.path.exists', return_value=False)
    @patch('os.mkdir')
    def test_make_subdirs(self, os_mkdir, _):
        test_module.MorphWriter._make_subdirs('/root', depth=1)
        assert os_mkdir.call_count == 257
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
        assert self.test_obj._dir_depth is None
        os_makedirs.assert_called_once_with('/root')

    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=[])
    def test_prepare_2(self, _, _2):
        self.test_obj.prepare(2 ** 10)
        assert self.test_obj._dir_depth is None

    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=['a'])
    def test_prepare_3(self, _, _2):
        with pytest.raises(RuntimeError, match="Non-empty morphology output folder"):
            self.test_obj.prepare(2 ** 10)

    @patch('os.path.exists', return_value=True)
    @patch('os.listdir', return_value=['a'])
    def test_prepare_4(self, _, _2):
        self.test_obj.prepare(2 ** 10, overwrite=True)
        assert self.test_obj._dir_depth is None

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
        assert (
            self.test_obj._generate_name(42) == ('bdd640fb06671ad11c80317fa3b1799d', '')
        )

    def test_generate_name_2(self):
        self.test_obj._dir_depth = 2
        assert (
            self.test_obj._generate_name(42) == ('bdd640fb06671ad11c80317fa3b1799d', 'hashed/bd/d6')
        )

    @patch('morphio.mut.Morphology')
    def test_call(self, morph_cls):
        import morphio
        self.test_obj._dir_depth = 2
        path = self.test_obj('morph-obj', 42)
        assert path == 'hashed/bd/d6/bdd640fb06671ad11c80317fa3b1799d'
        morph_cls.assert_has_calls([
            mock.call('morph-obj', options=morphio.Option.nrn_order),
            mock.call().write(Path('/root/hashed/bd/d6/bdd640fb06671ad11c80317fa3b1799d.asc')),
            mock.call().write(Path('/root/hashed/bd/d6/bdd640fb06671ad11c80317fa3b1799d.swc')),
        ])
