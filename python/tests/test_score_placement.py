import os
import unittest

import pandas as pd
import nose.tools as nt
import numpy.testing as npt

import score_placement as test_module


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(TEST_DIR, "../../tests/data")


def test_y_absolute():
    candidate = { 'L2_0': 1, 'L2_1': 2 }
    actual = test_module.y_absolute(('L2', 0.1), candidate)
    nt.assert_equal(actual, 1.1)


def test_y_below_rule():
    rule = test_module.YBelowRule(y_rel=('L1', 0.5), tolerance=10.0)
    candidate = { 'y': 10, 'L1_0': 20, 'L1_1': 30 }
    nt.assert_equal(rule(candidate, {'y_max': 16}), 0.9)
    nt.assert_equal(rule(candidate, {'y_max':  0}), 1.0)
    nt.assert_equal(rule(candidate, {'y_max': 50}), 0.0)


def test_y_range_overlap():
    rule = test_module.YRangeOverlapRule(y_rel_min=('L1', 0.0), y_rel_max=('L1', 0.5))
    candidate = { 'y': 20, 'L1_0': 20, 'L1_1': 30 }
    nt.assert_equal(rule(candidate, {'y_min': -4, 'y_max': -2}), 0.0)
    nt.assert_equal(rule(candidate, {'y_min': -2, 'y_max':  2}), 0.5)
    nt.assert_equal(rule(candidate, {'y_min':  2, 'y_max':  4}), 1.0)


def test_generalized_mean():
    nt.assert_almost_equal(
        test_module.generalized_mean([1., 2., 3., 4.], p=5.0),
        3.1796306
    )
    nt.assert_almost_equal(
        test_module.generalized_mean([1., 2., 3., 4.], p=1.0),
        2.5
    )
    nt.assert_almost_equal(
        test_module.generalized_mean([1., 2., 3., 4.], p=-3.0),
        1.5031873
    )


def test_aggregate_optional_scores():
    nt.assert_equal(
        test_module.aggregate_optional_scores([], 1.0),
        0.1
    )
    nt.assert_almost_equal(
        test_module.aggregate_optional_scores([0.0, 0.5, 1.0], p=1.0),
        0.5
    )
    nt.assert_almost_equal(
        test_module.aggregate_optional_scores([0.0, 0.5, 1.0], p=10.0),
        0.801927386
    )
    nt.assert_almost_equal(
        test_module.aggregate_optional_scores([0.0, 0.5, 1.0], p=-10.0),
        0.114098987
    )


def test_aggregate_strict_scores():
    nt.assert_equal(
        test_module.aggregate_strict_scores([]),
        1.0
    )
    nt.assert_almost_equal(
        test_module.aggregate_strict_scores([0.1, 0.2, 0.3, 0.4]),
        0.1
    )


def test_load_annotation():
    expected = [
        {'rule': 'L1_HAC, axon, Layer_1', 'y_min': '-70.0', 'y_max': '46.0' },
        {'rule': 'L1_hard_limit', 'y_min': '-223.907318115', 'y_max': '33.7012710571' },
        {'rule': 'L1_axon_hard_limit', 'y_min': '-217.9246521', 'y_max': '38.8493537903' },
    ]
    result = test_module.load_annotation(os.path.join(TEST_DATA_DIR, "C060106F.xml"))
    nt.assert_equal(expected, result)


def test_load_rules():
    result = test_module.load_rules(os.path.join(TEST_DATA_DIR, "rules.xml"))
    nt.assert_is_instance(result['L1_hard_limit'], test_module.YBelowRule)
    nt.assert_is_instance(result['L1_HAC, axon, Layer_1'], test_module.YRangeOverlapRule)
