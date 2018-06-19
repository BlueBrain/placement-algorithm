import nose.tools as nt
import numpy.testing as npt

from cStringIO import StringIO

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
    rules = StringIO("""
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
