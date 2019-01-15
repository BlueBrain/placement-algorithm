"""
Module encapsulating placement algorithm per se:
 - score calculation for each rule
 - score aggregation
 - choosing morphology based on its score
"""

import numpy as np
import pandas as pd

from six import iteritems


def y_absolute(y_rel, position):
    """ Given position layer profile, convert (layer, fraction) pair to absolute Y value. """
    layer, fraction = y_rel
    y0 = position[layer + "_0"]
    y1 = position[layer + "_1"]
    return (1.0 - fraction) * y0 + fraction * y1


class Rule(object):
    """ Base class for rule functors. """
    def __init__(self, segment_type, strict):
        if segment_type not in ('axon', 'dendrite'):
            raise ValueError("Invalid segment type: '%s'" % segment_type)
        self.segment_type = segment_type
        self.strict = strict


class BelowRule(Rule):
    """
    Check that 'y' does not exceed given limit.

    score = 1.0 - clip((y_position - y_annotation) / tolerance, 0.0, 1.0).

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#below
    """

    ANNOTATION_PARAMS = ['y_max']

    def __init__(self, y_rel, tolerance, segment_type):
        super(BelowRule, self).__init__(segment_type, strict=True)
        self.y_rel = y_rel
        self.tolerance = tolerance

    @classmethod
    def from_xml(cls, elem):
        """ Instantiate from XML element. """
        attr = elem.attrib
        return cls(
            y_rel=(attr['y_layer'], float(attr['y_fraction'])),
            tolerance=float(attr.get('tolerance', 30.0)),
            segment_type=attr['segment_type']
        )

    def __call__(self, position, annotation, scale=1.0):
        y_limit = y_absolute(self.y_rel, position)
        delta = (position['y'] + scale * annotation['y_max'].values) - y_limit
        result = 1.0 - delta / self.tolerance
        result = np.clip(result, a_min=0.0, a_max=1.0)
        return pd.Series(result, index=annotation.index)


class RegionTargetRule(Rule):
    """
    Check that '[y1; y2]' falls within given interval.

    score = overlap(position, annotation) / max_possible_overlap(position, annotation)

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#region-target
    """

    ANNOTATION_PARAMS = ['y_min', 'y_max']

    def __init__(self, y_rel_min, y_rel_max, segment_type):
        super(RegionTargetRule, self).__init__(segment_type, strict=False)
        self.y_rel_min = y_rel_min
        self.y_rel_max = y_rel_max

    @classmethod
    def from_xml(cls, elem):
        """ Instantiate from XML element. """
        attr = elem.attrib
        return cls(
            y_rel_min=(attr['y_min_layer'], float(attr['y_min_fraction'])),
            y_rel_max=(attr['y_max_layer'], float(attr['y_max_fraction'])),
            segment_type=attr['segment_type']
        )

    @staticmethod
    def _score_overlap(y1, y2, y1c, y2c):
        y1o = np.maximum(y1, y1c)  # pylint: disable=assignment-from-no-return
        y2o = np.minimum(y2, y2c)  # pylint: disable=assignment-from-no-return
        return np.where(
            y2o > y1o,
            (y2o - y1o) / np.minimum(y2 - y1, y2c - y1c),
            0.0
        )

    def __call__(self, position, annotation, scale=1.0):
        y1 = y_absolute(self.y_rel_min, position)
        y2 = y_absolute(self.y_rel_max, position)
        if np.isclose(y1, y2):
            return pd.Series(0.0, index=annotation.index)
        y1c = position['y'] + scale * annotation['y_min'].values
        y2c = position['y'] + scale * annotation['y_max'].values
        score = self._score_overlap(y1, y2, y1c, y2c)
        return pd.Series(score, index=annotation.index)


class RegionOccupyRule(RegionTargetRule):
    """
    Check that '[y1; y2]' *occupies* given interval.

    score = overlap(position, annotation) / max_range(position, annotation)

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#region-occupy
    """
    @staticmethod
    def _score_overlap(y1, y2, y1c, y2c):
        y1o = np.maximum(y1, y1c)  # pylint: disable=assignment-from-no-return
        y2o = np.minimum(y2, y2c)  # pylint: disable=assignment-from-no-return
        return np.where(
            y2o > y1o,
            (y2o - y1o) / np.maximum(y2 - y1, y2c - y1c),
            0.0
        )


def aggregate_strict_score(scores):
    """
    Aggregate strict scores.

      - NaNs are filtered out
      - for empty score vector, return 1.0
      - otherwise, take the minimum of all scores

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#combining-the-scores
    """
    return scores.min(axis=1, skipna=True).fillna(1.0)


def _hmean(xs, eps=1e-5):
    xs = np.asarray(xs)
    mask = np.isnan(xs)
    if np.all(mask):
        return np.nan
    xs = xs[~mask]
    if np.any(xs < eps):
        return 0.0
    return len(xs) / np.sum(1.0 / xs)


def aggregate_optional_score(scores):
    """
    Aggregate optional scores.

        - NaNs are filted out
        - for empty score vector, return 1.0
        - if some score is too low (<1e-5), return 0.0
        - otherwise, take harmonic mean of all scores

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#combining-the-scores
    """
    return scores.apply(_hmean, axis=1).fillna(1.0)


def _scale_bias(scale):
    if scale > 1.0:
        return 1.0 / scale
    else:
        return scale


def score_morphologies(position, rules, params, scale=1.0, segment_type=None):
    """
    Calculate placement score for a batch of annotated morphologies.

    Args:
        position: layer profile (a mapping with 'y' + '<layer>_[0|1]' values)
        rules: dict of placement rules functors
        params: pandas DataFrame with morphology annotations
        scale: scale factor along Y-axis
        segment_type: if specified, check only corresponding rules ('axon' or 'dendrite')

    Returns:
        pandas DataFrame with aggregated scores;
            rows correspond to morphologies,
            columns correspond to strict / optional / total scores.

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#combining-the-scores
    """
    result = pd.DataFrame(index=params.index)
    strict, optional = [], []
    for rule_id, rule in iteritems(rules):
        if (segment_type is not None) and (rule.segment_type != segment_type):
            continue
        annotation = params[rule_id].dropna()
        result[rule_id] = rule(position=position, annotation=annotation, scale=scale)
        if rule.strict:
            strict.append(rule_id)
        else:
            optional.append(rule_id)
    result['strict'] = aggregate_strict_score(result[strict])
    result['optional'] = aggregate_optional_score(result[optional])
    result['total'] = result['strict'] * result['optional'] * _scale_bias(scale)
    return result


def choose_morphology(position, rules, params, alpha=1.0, scales=None, segment_type=None):
    """
    Choose morphology from a list of annotated morphologies.

    Args:
        position: layer profile (a mapping with 'y' + '<layer>_[0|1]' values)
        rules: dict of placement rules functors
        params: pandas DataFrame with morphology annotations
        alpha: exponential factor for scores
        scales: list of scales to choose from
        segment_type: if specified, check only corresponding rules ('axon' or 'dendrite')

    Returns:
        Morphology picked at random with scores ** alpha as probability weights
        (`None` if all the morphologies score 0).
    """
    if scales is None:
        scores = score_morphologies(position, rules, params, segment_type=segment_type)
    else:
        scores = {}
        for scale in scales:
            scores[scale] = score_morphologies(
                position, rules, params, scale=scale, segment_type=segment_type
            )
        scores = pd.concat(scores).swaplevel()
    weights = scores['total'].values ** alpha
    w_sum = np.sum(weights)
    if np.isclose(w_sum, 0.0):
        return None
    return np.random.choice(scores.index.values, p=weights / w_sum)
