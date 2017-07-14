import nose.tools as nt
import numpy.testing as npt

from cStringIO import StringIO

import calc_all_scores as test_module


def test_load_morphdb():
    MORPHDB = StringIO("""
    morph-A 2 mtype-A etype-A ...
    morph-B 3 mtype-B etype-B ...
    """)
    actual = test_module.load_morphdb(MORPHDB)
    expected = [
        (('2', 'mtype-A', 'etype-A'), 'morph-A'),
        (('3', 'mtype-B', 'etype-B'), 'morph-B'),
    ]
    nt.assert_equal(actual, expected)

def test_drop_key():
    actual = test_module.drop_key(("A", "B"))
    expected = "B"
    return nt.assert_equal(actual, expected)

def test_format_candidate():
    elem = ("A", ("3:1", 42.0, {'L2': (2.0, 3.0), 'L1': (1.0, 2.0)}))
    actual = test_module.format_candidate(elem, ['L1', 'L2'])
    expected = "A 3:1 42.000 1.000 2.000 2.000 3.000"
    nt.assert_equal(actual, expected)

def test_parse_score():
    actual = test_module.parse_score("A 3 0.42")
    expected = ("3", (0.42, "A"))
    nt.assert_equal(actual, expected)
