import nose.tools as nt
import numpy.testing as npt

from cStringIO import StringIO

import calc_all_scores as test_module


def test_parse_morphdb():
    actual = test_module.parse_morphdb("morph-A 2 mtype-A etype-A ...")
    expected = (("morph-A", "mtype-A"), ("2", "mtype-A", "etype-A"))
    nt.assert_equal(actual, expected)

def test_parse_positions():
    actual = test_module.parse_positions("gid 2 mtype-A etype-A 1.0 11.0 12.0 21.0 22.0")
    expected = (("2", "mtype-A", "etype-A"), ("gid", "1.0", "11.0 12.0 21.0 22.0"))
    nt.assert_equal(actual, expected)

def test_format_candidate():
    elem = (("mtype-A", "morph-A"), ("gid", "1.0", "11.0 12.0 21.0 22.0"))
    actual = test_module.format_candidate(elem)
    expected = "mtype-A morph-A gid 1.0 11.0 12.0 21.0 22.0"
    nt.assert_equal(actual, expected)

def test_parse_score():
    actual = test_module.parse_score("morph-A 42 0.42")
    expected = ("42", ("morph-A", 0.42))
    nt.assert_equal(actual, expected)

def test_pick_morph_1():
    actual = test_module.pick_morph(("42", [("morph-A", 0.), ("morph-B", 0.)]))
    expected = [
        ("42", ("N/A", 0.0)),
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
        (11, ("N/A", 0.0)),
        (22, ("N/A", 0.0)),
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
