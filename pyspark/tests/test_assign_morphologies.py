import nose.tools as nt
import numpy as np
import numpy.testing as npt
from mock import Mock

import pandas as pd
import xml.etree.ElementTree as ET

import assign_morphologies as test_module


def test_format_candidate():
    elem = (("mtype-A", "morph-A"), ("gid", [1.0, 11.0]))
    actual = test_module.format_candidate(elem)
    expected = "mtype-A morph-A gid 1.0 11.0"
    nt.assert_equal(actual, expected)

def test_parse_score():
    actual = test_module.parse_score("morph-A 42 0.42")
    expected = ("42", ("morph-A", 0.42))
    nt.assert_equal(actual, expected)

def test_pick_morph_1():
    actual = test_module.pick_morph(("42", [("morph-A", 0.), ("morph-B", 0.)]))
    expected = [
        ("42", (None, 0.0)),
    ]
    nt.assert_equal(actual, expected)

def test_pick_morph_2():
    actual = test_module.pick_morph(("42", [("morph-A", 0.1), ("morph-B", 0.)]))
    expected = [
        ("42", ("morph-A", 0.1)),
    ]
    nt.assert_equal(actual, expected)

def test_pick_morph_3():
    index = {"42": [11, 22]}
    actual = test_module.pick_morph(("42", [("morph-A", 0.), ("morph-B", 0.)]), index=index)
    expected = [
        (11, (None, 0.0)),
        (22, (None, 0.0)),
    ]
    nt.assert_equal(actual, expected)

def test_pick_morph_4():
    index = {"42": [11, 22]}
    actual = test_module.pick_morph(("42", [("morph-A", 0.1), ("morph-B", 0.)]), index=index)
    expected = [
        (11, ("morph-A", 0.1)),
        (22, ("morph-A", 0.1)),
    ]
    nt.assert_equal(actual, expected)


def test_collect_layer_names():
    rules = ET.fromstring("""
        <placement_rules>
            <global_rule_set>
                <rule y_layer="1" />
                <rule y_layer="2" />
            </global_rule_set>
            <mtype_rule_set>
                <rule y_min_layer="4" y_max_layer="5" />
            </mtype_rule_set>
        </placement_rules>
    """)
    actual = test_module.collect_layer_names(rules)
    expected = set(['1', '2', '4', '5'])
    nt.assert_equal(actual, expected)


def test_parse_rotations():
    rules = ET.fromstring("""
        <placement_rules>
            <global_rotation>
                <rotation axis="y" distr="foo" />
            </global_rotation>
            <mtype_rotation mtype="mtype-A">
                <rotation axis="x" distr="bar" />
                <rotation axis="z" distr="baz" />
            </mtype_rotation>
        </placement_rules>
    """)
    global_conf, mtype_conf = test_module.parse_rotations(rules)
    nt.assert_equal(global_conf, [('y', 'foo')])
    nt.assert_equal(mtype_conf, {'mtype-A': [('x', 'bar'), ('z', 'baz')]})


def test_assign_orientations():
    cells = Mock()
    cells.properties = pd.DataFrame({
        'mtype': ["mtype-A", "mtype-B", "mtype-A"]
    })
    orientation_field = Mock()
    atlas = Mock()
    atlas.load_data.return_value = orientation_field
    rules = ET.fromstring("""
        <placement_rules>
            <global_rotation>
                <!-- rotate around Y-axis by PI -->
                <rotation axis="y" distr='["uniform", {"a": 3.14159265, "b": 3.14159265}]' />
            </global_rotation>
            <mtype_rotation mtype="mtype-A">
                <!-- suppress random rotation -->
            </mtype_rotation>
        </placement_rules>
    """)
    A = np.identity(3)
    orientation_field.lookup.return_value = np.array([A, A, A])
    test_module.assign_orientations(cells, atlas, rules)
    nt.assert_equal(cells.orientations.shape[0], 3)
    npt.assert_almost_equal(cells.orientations[0], A)
    npt.assert_almost_equal(cells.orientations[1], [[-1, 0, 0], [0, 1, 0], [0, 0, -1]])
    npt.assert_almost_equal(cells.orientations[2], A)
