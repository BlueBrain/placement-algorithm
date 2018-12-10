import os

import lxml.etree
import numpy as np
import pandas as pd

import mock
import nose.tools as nt
import numpy.testing as npt
import pandas.util.testing as pdt

from mock import patch, Mock

from placement_algorithm.exceptions import PlacementError

import placement_algorithm.files as test_module


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _test_data_path(filename):
    return os.path.join(TEST_DATA_DIR, filename)


@patch(test_module.__name__ + ".LOGGER")
def test_placement_rules_parse(logger):
    rules = test_module.PlacementRules(_test_data_path('rules.xml'))
    logger.warn.assert_called_once_with(mock.ANY, 'prefer_unscaled')
    nt.assert_equal(
        sorted(rules.common_rules),
        ['L1_axon_hard_limit', 'L1_hard_limit']
    )
    nt.assert_equal(
        sorted(rules.mtype_rules),
        ['L1_HAC', 'L1_SAC']
    )
    mtype_rules = rules.mtype_rules['L1_HAC']
    nt.assert_equal(
        sorted(mtype_rules),
        ['L1_axon_hard_limit', 'L1_hard_limit', 'axon, Layer_1', 'axon, Layer_1, fill']
    )
    nt.assert_is_instance(mtype_rules['L1_axon_hard_limit'], test_module.YBelowRule)
    nt.assert_is_instance(mtype_rules['L1_hard_limit'], test_module.YBelowRule)
    nt.assert_is_instance(mtype_rules['axon, Layer_1'], test_module.YRangeOverlapRule)
    nt.assert_is_instance(mtype_rules['axon, Layer_1, fill'], test_module.YRangeOverlapRule)
    nt.assert_equal(rules.layer_names, set(['1', '2']))


def test_placement_rules_empty():
    etree = lxml.etree.fromstring("""
    <placement_rules>
    </placement_rules>
    """)
    common_rules, mtype_rules = test_module._parse_rules(etree)
    nt.assert_false(common_rules)
    nt.assert_false(mtype_rules)


def test_placement_rules_duplicate_global_rules():
    etree = lxml.etree.fromstring("""
    <placement_rules>
        <global_rule_set />
        <global_rule_set />
    </placement_rules>
    """)
    nt.assert_raises(
        PlacementError,
        test_module._parse_rules, etree
    )


def test_placement_rules_duplicate_mtype_rules():
    etree = lxml.etree.fromstring("""
    <placement_rules>
        <mtype_rule_set mtype="A|C" />
        <mtype_rule_set mtype="B|C" />
    </placement_rules>
    """)
    nt.assert_raises(
        PlacementError,
        test_module._parse_rules, etree
    )


def test_placement_rules_duplicate_rule_id():
    elem = lxml.etree.fromstring("""
    <rule_set>
        <rule id="id-1" type="below" segment_type="dendrite" y_layer="1" y_fraction="1.0"/>
        <rule id="id-1" type="below" segment_type="axon" y_layer="1" y_fraction="1.0"/>
    </rule_set>
    """)
    nt.assert_raises(
        PlacementError,
        test_module._parse_rule_set, elem
    )


@patch(test_module.__name__ + ".LOGGER")
def test_placement_rules_bind(logger):
    rules = test_module.PlacementRules(_test_data_path('rules.xml'))
    annotations = {
        'morph-1': {
            'axon, Layer_1': {
                'y_min': '11.0',
            },
            'ScaleBias': {
            },
        },
        'morph-2': {
            'L1_hard_limit': {
                'y_max': '22.0',
                'foo': 'test',
            },
        }
    }
    expected = pd.DataFrame(
        [
            [np.nan, np.nan],
            [np.nan, 22.0],
        ],
        index=['morph-1', 'morph-2'],
        columns=[['L1_axon_hard_limit', 'L1_hard_limit'], ['y_max', 'y_max']]
    )
    mtype_rules, params = rules.bind(annotations, 'undefined-mtype')
    nt.assert_equal(
        sorted(mtype_rules.keys()),
        ['L1_axon_hard_limit', 'L1_hard_limit']
    )
    nt.assert_equal(
        sorted(params.columns),
        [
            ('L1_axon_hard_limit', 'y_max'),
            ('L1_hard_limit', 'y_max'),
        ]
    )
    pdt.assert_frame_equal(params, expected)
    mtype_rules, params = rules.bind(annotations, 'L1_SAC')
    nt.assert_equal(
        sorted(mtype_rules.keys()),
        ['L1_axon_hard_limit', 'L1_hard_limit', 'axon, Layer_1', 'axon, Layer_1, fill']
    )
    nt.assert_equal(
        sorted(params.columns),
        [
            ('L1_axon_hard_limit', 'y_max'),
            ('L1_hard_limit', 'y_max'),
            ('axon, Layer_1', 'y_max'),
            ('axon, Layer_1', 'y_min'),
            ('axon, Layer_1, fill', 'y_max'),
            ('axon, Layer_1, fill', 'y_min'),
        ]
    )
    logger.warn.assert_has_calls([
        mock.ANY,
        mock.call(mock.ANY, 'axon, Layer_1', 'morph-1'),
    ])


def test_parse_annotations():
    actual = test_module.parse_annotations(_test_data_path('C060106F.xml'))
    expected = {
        'axon, Layer_1': {
            'y_min': '-70.0',
            'y_max': '46.0',
        },
        'L1_hard_limit': {
            'y_min': '-223.907318115',
            'y_max': '33.7012710571',
        },
        'L1_axon_hard_limit': {
            'y_min': '-217.9246521',
            'y_max': '38.8493537903',
        },
        'ScaleBias': {}
    }
    nt.assert_equal(actual, expected)


@patch('lxml.etree.parse')
def test_annotations_duplicate_rule_id(etree_mock):
    etree = lxml.etree.fromstring("""
    <annotations>
        <placement rule="id-1" />
        <placement rule="id-1" />
    </annotations>
    """)
    etree_mock.configure_mock(return_value=etree)
    nt.assert_raises(
        PlacementError,
        test_module.parse_annotations, None
    )


def test_parse_morphdb():
    actual = test_module.parse_morphdb(_test_data_path('extNeuronDB.dat'))
    expected = pd.DataFrame(
        [
            ('C060106F', 1, 'L1_HAC', 'bAC'),
            ('C060106F', 1, 'L1_HAC', 'cNAC'),
            ('morph-C', 1, 'L1_HAC', 'bAC'),
            ('morph-D', 1, 'L1_HAC', 'cNAC'),
        ],
        columns=['morphology', 'layer', 'mtype', 'etype']
    )
    pdt.assert_frame_equal(actual, expected)
