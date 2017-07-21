import nose.tools as nt
import numpy.testing as npt

from cStringIO import StringIO

import calc_all_scores as test_module


def test_parse_morphdb():
    actual = test_module.parse_morphdb("morph-A 2 mtype-A etype-A ...")
    expected = (("2", "mtype-A", "etype-A"), "morph-A")
    nt.assert_equal(actual, expected)

def test_parse_positions():
    actual = test_module.parse_positions("gid 2 mtype-A etype-A 1.0 11.0 12.0 21.0 22.0")
    expected = (("2", "mtype-A", "etype-A"), ("gid", "1.0", "11.0 12.0 21.0 22.0"))
    nt.assert_equal(actual, expected)

def test_drop_key():
    actual = test_module.drop_key(("A", "B"))
    expected = "B"
    return nt.assert_equal(actual, expected)

def test_format_candidate():
    elem = ("morph-A", ("gid", "1.0", "11.0 12.0 21.0 22.0"))
    actual = test_module.format_candidate(elem)
    expected = "morph-A gid 1.0 11.0 12.0 21.0 22.0"
    nt.assert_equal(actual, expected)

def test_parse_score():
    actual = test_module.parse_score("morph-A gid 0.42")
    expected = ("gid", ("morph-A", 0.42))
    nt.assert_equal(actual, expected)

def test_pick_morph_1():
    actual = test_module.pick_morph([("morph-A", 0.), ("morph-B", 0.)])
    expected = "<none>"
    nt.assert_equal(actual, expected)

def test_pick_morph_2():
    actual = test_module.pick_morph([("morph-A", 0.1), ("morph-B", 0.)])
    expected = "morph-A"
    nt.assert_equal(actual, expected)

