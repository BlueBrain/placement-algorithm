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


class YBelowRule(object):
    """
    Check that 'y' does not exceed given limit.

    score = 1.0 - clip((y_position - y_annotation) / tolerance, 0.0, 1.0).

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#below
    """

    ANNOTATION_PARAMS = ['y_max']

    def __init__(self, y_rel, tolerance):
        self.y_rel = y_rel
        self.tolerance = tolerance

    @classmethod
    def from_xml(cls, elem):
        """ Instantiate from XML element. """
        attr = elem.attrib
        return cls(
            y_rel=(attr['y_layer'], float(attr['y_fraction'])),
            tolerance=float(attr.get('tolerance', 30.0))
        )

    def __call__(self, position, annotation):
        y_limit = y_absolute(self.y_rel, position)
        delta = (position['y'] + annotation['y_max'].values) - y_limit
        result = 1.0 - delta / self.tolerance
        result = np.clip(result, a_min=0.0, a_max=1.0)
        return pd.Series(result, index=annotation.index)

    @property
    def strict(self):
        """ Whether it's strict or optional rule. """
        return True


class YRangeOverlapRule(object):
    """
    Check that '[y1; y2]' falls within given interval.

    score = overlap(position, annotation) / max_possible_overlap(position, annotation)

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#region-target
    """

    ANNOTATION_PARAMS = ['y_min', 'y_max']

    def __init__(self, y_rel_min, y_rel_max):
        self.y_rel_min = y_rel_min
        self.y_rel_max = y_rel_max

    @classmethod
    def from_xml(cls, elem):
        """ Instantiate from XML element. """
        attr = elem.attrib
        return cls(
            y_rel_min=(attr['y_min_layer'], float(attr['y_min_fraction'])),
            y_rel_max=(attr['y_max_layer'], float(attr['y_max_fraction']))
        )

    def __call__(self, position, annotation):
        y1 = y_absolute(self.y_rel_min, position)
        y2 = y_absolute(self.y_rel_max, position)
        if np.isclose(y1, y2):
            return pd.Series(0.0, index=annotation.index)
        y1c = position['y'] + annotation['y_min'].values
        y2c = position['y'] + annotation['y_max'].values
        y1o = np.maximum(y1, y1c)
        y2o = np.minimum(y2, y2c)
        score = np.where(
            y2o > y1o,
            (y2o - y1o) / np.minimum(y2 - y1, y2c - y1c),
            0.0
        )
        return pd.Series(score, index=annotation.index)

    @property
    def strict(self):
        """ Whether it's strict or optional rule. """
        return False


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


def score_morphologies(position, rules, params):
    """
    Calculate placement score for a batch of annotated morphologies.

    Args:
        position: layer profile (a mapping with 'y' + '<layer>_[0|1]' values)
        rules: dict of placement rules functors
        params: pandas DataFrame with morphology annotations

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
        annotation = params[rule_id].dropna()
        result[rule_id] = rule(position=position, annotation=annotation)
        if rule.strict:
            strict.append(rule_id)
        else:
            optional.append(rule_id)
    result['strict'] = aggregate_strict_score(result[strict])
    result['optional'] = aggregate_optional_score(result[optional])
    result['total'] = result['strict'] * result['optional']
    return result


def choose_morphology(position, rules, params, alpha=1.0, seed=None, return_scores=False):
    """
    Choose morphology from a list of annotated morphologies.

    Args:
        position: layer profile (a mapping with 'y' + '<layer>_[0|1]' values)
        rules: dict of placement rules functors
        params: pandas DataFrame with morphology annotations
        alpha: exponential factor for scores
        seed: pseudo-random seed generator (for reproducibility)

    Returns:
        Morphology picked on random with scores ** alpha as probability weights
        (`None` if all the morphologies score 0).
    """
    scores = score_morphologies(position, rules, params)
    morphs = scores.index.values
    weights = scores['total'].values ** alpha
    w_sum = np.sum(weights)
    if np.isclose(w_sum, 0.0):
        result = None
    else:
        if seed is not None:
            np.random.seed(seed % (1 << 32))
        result = np.random.choice(morphs, p=weights / w_sum)
    if return_scores:
        return result, scores
    else:
        return result
