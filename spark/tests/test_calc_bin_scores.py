import nose.tools as nt
import numpy.testing as npt

import calc_bin_scores as test_module


def test_parse_morphdb():
    actual = test_module.parse_morphdb("A 3 mtype ...")
    expected = ("A", "3")
    nt.assert_equal(actual, expected)

def test_get_layer_bins():
    actual = test_module.get_layer_bins(0, 100, 23)
    expected = [12.5, 37.5, 62.5, 87.5]
    npt.assert_equal(actual, expected)

def test_morph_candidates():
    layer_profile = {'3': (0, 10), '4': (20, 30)}
    actual = test_module.morph_candidates(("A", "3"), layer_profile, binsize=5)
    expected = [
        ('A', ('3:0', 2.5, layer_profile)),
        ('A', ('3:1', 7.5, layer_profile))
    ]
    nt.assert_equal(actual, expected)

def test_format_candidate():
    elem = ("A", ("3:1", 42.0, {'L2': (2.0, 3.0), 'L1': (1.0, 2.0)}))
    actual = test_module.format_candidate(elem, ['L1', 'L2'])
    expected = "A 3:1 42.000 1.000 2.000 2.000 3.000"
    nt.assert_equal(actual, expected)

def test_parse_score():
    actual = test_module.parse_score("A 3:1 0.42")
    expected = (("A", "3"), (1, 0.42))
    nt.assert_equal(actual, expected)

def test_format_bin_scores():
    actual = test_module.format_bin_scores((("A", "3"), [(1, 0.0), (3, 0.2345), (2, 0.1)]))
    expected = "A 3 0.000 0.100 0.234"
    nt.assert_equal(actual, expected)
