import numpy as np
import pandas as pd

import mock
import nose.tools as nt
import numpy.testing as npt
from pandas.testing import assert_frame_equal, assert_series_equal


import placement_algorithm.algorithm as test_module


def test_y_absolute():
    position = {'L1_0': 0, 'L1_1': 100}
    actual = test_module.y_absolute(('L1', 0.25), position)
    nt.assert_equal(actual, 25)


def test_invalid_segment_type():
    nt.assert_raises(
        ValueError,
        test_module.Rule, segment_type='soma', strict=True
    )


def test_below_rule_create():
    elem = mock.Mock(attrib={
        'y_layer': 'L1',
        'y_fraction': 0.5,
        'tolerance': 50.0,
        'segment_type': 'axon'
    })
    rule = test_module.BelowRule.from_xml(elem)
    nt.assert_equal(rule.y_rel, ('L1', 0.5))
    nt.assert_equal(rule.tolerance, 50.0)
    nt.assert_true(rule.strict)
    nt.assert_equal(rule.segment_type, 'axon')
    nt.assert_equal(rule.ANNOTATION_PARAMS, ['y_max'])


def test_below_rule():
    rule = test_module.BelowRule(
        y_rel=('L1', 0.5), tolerance=30.0, segment_type='axon'
    )
    position = {'y': 110.0, 'L1_0': 100, 'L1_1': 200}
    annotations = pd.DataFrame({
        'y_max': [71.0, 55.0, 39.0],
    }, index=list('abc'))
    assert_series_equal(
        rule(position, annotations),
        pd.Series([0.0, 0.5, 1.0], index=annotations.index)
    )


def test_region_target_rule_create():
    elem = mock.Mock(attrib={
        'y_min_layer': 'L1',
        'y_min_fraction': 0.0,
        'y_max_layer': 'L1',
        'y_max_fraction': 0.5,
        'segment_type': 'dendrite'
    })
    rule = test_module.RegionTargetRule.from_xml(elem)
    nt.assert_equal(rule.y_rel_min, ('L1', 0.0))
    nt.assert_equal(rule.y_rel_max, ('L1', 0.5))
    nt.assert_false(rule.strict)
    nt.assert_equal(rule.segment_type, 'dendrite')
    nt.assert_equal(rule.ANNOTATION_PARAMS, ['y_min', 'y_max'])


def test_region_target_rule_1():
    rule = test_module.RegionTargetRule(
        y_rel_min=('L1', 0.0),  y_rel_max=('L1', 0.5), segment_type='axon'
    )
    position = {'y': 20.0, 'L1_0': 20.0, 'L1_1': 30.0}
    annotations = pd.DataFrame({
        'y_min': [-4.0, -2.0, 2.0],
        'y_max': [-2.0,  2.0, 3.0],
    }, index=list('abc'))
    assert_series_equal(
        rule(position, annotations),
        pd.Series([0.0, 0.5, 1.0], index=annotations.index)
    )


def test_region_target_rule_2():
    rule = test_module.RegionTargetRule(
        y_rel_min=('L1', 0.0),  y_rel_max=('L1', 0.5), segment_type='dendrite'
    )
    position = {'y': 20.0, 'L1_0': 20.0, 'L1_1': 20.0}  # 'L1' is empty
    annotations = pd.DataFrame({
        'y_min': [-4.0, -2.0, 2.0],
        'y_max': [-2.0,  2.0, 3.0],
    }, index=list('abc'))
    assert_series_equal(
        rule(position, annotations),
        pd.Series(0.0, index=annotations.index)
    )


def test_region_occupy_rule_1():
    rule = test_module.RegionOccupyRule(
        y_rel_min=('L1', 0.0),  y_rel_max=('L1', 0.5), segment_type='axon'
    )
    position = {'y': 20.0, 'L1_0': 20.0, 'L1_1': 30.0}
    annotations = pd.DataFrame({
        'y_min': [-4.0, -2.0, 2.0],
        'y_max': [-2.0,  2.0, 3.0],
    }, index=list('abc'))
    assert_series_equal(
        rule(position, annotations),
        pd.Series([0.0, 0.4, 0.2], index=annotations.index)
    )


def test_aggregate_strict_score():
    scores = pd.DataFrame([
        [   0.4,    0.2],
        [   0.1, np.nan],
        [np.nan, np.nan],
    ], index=list('abc'))
    assert_series_equal(
        test_module.aggregate_strict_score(scores),
        pd.Series([0.2, 0.1, 1.0], index=scores.index)
    )


def test_aggregate_strict_score_empty():
    scores = pd.DataFrame(index=list('ab'))
    assert_series_equal(
        test_module.aggregate_strict_score(scores),
        pd.Series([1.0, 1.0], index=scores.index)
    )


def test_aggregate_optional_score():
    scores = pd.DataFrame([
        [0.5,    1.0],
        [0.5, np.nan],
        [0.5,    0.0],
        [0.5,   1e-6],
        [np.nan, np.nan],
    ], index=list('abcde'))
    assert_series_equal(
        test_module.aggregate_optional_score(scores),
        pd.Series([0.666667, 0.5, 0.0, 0.0, 1.0], index=scores.index)
    )


def test_aggregate_optional_score_empty():
    scores = pd.DataFrame(index=list('ab'))
    assert_series_equal(
        test_module.aggregate_optional_score(scores),
        pd.Series([1.0, 1.0], index=scores.index)
    )

def test_scale_bias():
    npt.assert_almost_equal(test_module._scale_bias(1.0), 1.0)
    npt.assert_almost_equal(test_module._scale_bias(0.5), 0.5)
    npt.assert_almost_equal(test_module._scale_bias(2.0), 0.5)
    npt.assert_almost_equal(test_module._scale_bias(0.25), 0.25)
    npt.assert_almost_equal(test_module._scale_bias(4.0), 0.25)


def test_score_morphologies_1():
    position = {'y': 110.0, 'L1_0': 100, 'L1_1': 200}
    rules = {
        'rule-A': mock.Mock(
            strict=True,
            segment_type='axon',
            return_value=pd.Series([0.2], index=['morph-1'])
        ),
        'rule-B': mock.Mock(
            strict=True,
            segment_type='dendrite',
            return_value=pd.Series([0.3, 0.5], index=['morph-1', 'morph-2'])
        ),
        'rule-C': mock.Mock(
            strict=False,
            segment_type='axon',
            return_value=pd.Series([0.4, 0.6], index=['morph-1', 'morph-2'])
        ),
        'rule-D': mock.Mock(
            strict=False,
            segment_type='dendrite',
            return_value=pd.Series([0.7], index=['morph-2'])
        ),
    }
    params = pd.DataFrame({
        ('rule-A', 'y_max'): {'morph-1': 0, 'morph-2': np.nan},
        ('rule-B', 'y_max'): {'morph-1': 0, 'morph-2': 0},
        ('rule-C', 'y_min'): {'morph-1': 0, 'morph-2': 0},
        ('rule-C', 'y_min'): {'morph-1': 0, 'morph-2': 0},
        ('rule-D', 'y_max'): {'morph-1': np.nan, 'morph-2': 0},
        ('rule-D', 'y_max'): {'morph-1': np.nan, 'morph-2': 0},
    })
    actual = test_module.score_morphologies(position, rules, params)
    expected = pd.DataFrame(
        [
            [   0.2, 0.3, 0.4, np.nan, 0.2, 0.400000, 0.080000],
            [np.nan, 0.5, 0.6,    0.7, 0.5, 0.646154, 0.323077],
        ],
        index=['morph-1', 'morph-2'],
        columns=['rule-A', 'rule-B', 'rule-C', 'rule-D', 'strict', 'optional', 'total']
    )
    assert_frame_equal(actual, expected, check_like=True)


def test_score_morphologies_2():
    position = {'y': 110.0, 'L1_0': 100, 'L1_1': 200}
    rules = {
        'rule-A': mock.Mock(
            strict=True,
            segment_type='axon',
            return_value=pd.Series([0.2], index=['morph-1'])
        ),
        'rule-B': mock.Mock(
            strict=True,
            segment_type='dendrite',
            return_value=pd.Series([0.3, 0.5], index=['morph-1', 'morph-2'])
        ),
        'rule-C': mock.Mock(
            strict=False,
            segment_type='axon',
            return_value=pd.Series([0.4, 0.6], index=['morph-1', 'morph-2'])
        ),
        'rule-D': mock.Mock(
            strict=False,
            segment_type='dendrite',
            return_value=pd.Series([0.7], index=['morph-2'])
        ),
    }
    params = pd.DataFrame({
        ('rule-A', 'y_max'): {'morph-1': 0, 'morph-2': np.nan},
        ('rule-B', 'y_max'): {'morph-1': 0, 'morph-2': 0},
        ('rule-C', 'y_min'): {'morph-1': 0, 'morph-2': 0},
        ('rule-C', 'y_min'): {'morph-1': 0, 'morph-2': 0},
        ('rule-D', 'y_max'): {'morph-1': np.nan, 'morph-2': 0},
        ('rule-D', 'y_max'): {'morph-1': np.nan, 'morph-2': 0},
    })
    actual = test_module.score_morphologies(position, rules, params, segment_type='dendrite')
    expected = pd.DataFrame(
        [
            [0.3, np.nan, 0.3, 1.0, 0.30],
            [0.5,    0.7, 0.5, 0.7, 0.35],
        ],
        index=['morph-1', 'morph-2'],
        columns=['rule-B', 'rule-D', 'strict', 'optional', 'total']
    )
    assert_frame_equal(actual, expected, check_like=True)


@mock.patch('numpy.random')
@mock.patch('placement_algorithm.algorithm.score_morphologies')
def test_choose_morphology_1(score_mock, np_random_mock):
    scores = pd.DataFrame({
        'total': [0.1, 0.9]
    }, index=['morph-1', 'morph-2'])
    score_mock.configure_mock(**{'return_value': scores})
    test_module.choose_morphology('position', 'rules', 'params', alpha=2.0, segment_type='axon')
    score_mock.assert_called_once_with(
        'position', 'rules', 'params', segment_type='axon'
    )
    np.random.choice.assert_called_once()
    npt.assert_equal(np.random.choice.call_args[0][0], ['morph-1', 'morph-2'])
    npt.assert_almost_equal(np.random.choice.call_args[1]['p'], [0.012195, 0.987805])


@mock.patch('placement_algorithm.algorithm.score_morphologies')
def test_choose_morphology_2(score_mock):
    scores = pd.DataFrame({
        'total': [0.0, 1e-12]
    }, index=['morph-1', 'morph-2'])
    score_mock.configure_mock(**{'return_value': scores})
    actual = test_module.choose_morphology(mock.ANY, mock.ANY, mock.ANY, alpha=2.0)
    nt.assert_is_none(actual)


@mock.patch('numpy.random')
@mock.patch('placement_algorithm.algorithm.score_morphologies')
def test_choose_morphology_3(score_mock, np_random_mock):
    scores = pd.DataFrame({
        'total': [0.1, 0.9]
    }, index=['morph-1', 'morph-2'])
    score_mock.configure_mock(**{'return_value': scores})
    test_module.choose_morphology('position', 'rules', 'params', alpha=2.0, scales=[0.5, 2.0])
    score_mock.assert_has_calls([
        mock.call('position', 'rules', 'params', scale=0.5, segment_type=None),
        mock.call('position', 'rules', 'params', scale=2.0, segment_type=None),
    ])
    np.random.choice.assert_called_once()
    nt.assert_equal(
        sorted(np.random.choice.call_args[0][0]),
        [('morph-1', 0.5), ('morph-1', 2.0), ('morph-2', 0.5), ('morph-2', 2.0)]
    )


@mock.patch('placement_algorithm.algorithm.score_morphologies')
def test_choose_morphology_4(score_mock):
    scores = pd.DataFrame({
        'total': [0.0, 1e-12]
    }, index=['morph-1', 'morph-2'])
    score_mock.configure_mock(**{'return_value': scores})
    actual = test_module.choose_morphology(mock.ANY, mock.ANY, mock.ANY, alpha=2.0, scales=[0.5, 2.0])
    nt.assert_is_none(actual)
