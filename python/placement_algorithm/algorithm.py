"""
Module encapsulating placement algorithm per se:
 - score calculation for each rule
 - score aggregation
 - choosing morphology based on its score
"""
from enum import Enum

import numpy as np
import pandas as pd
from scipy.stats import norm

UNIFORM_BIAS = "uniform"
LINEAR_BIAS = "linear"
GAUSSIAN_BIAS = "gaussian"


class COMPUTE_OPTIONAL_SCORES(Enum):
    """Enum used to define whether optional scores are computed and used or not."""
    DO_NOT_COMPUTE = 0
    COMPUTE_ONLY = 1
    COMPUTE_AND_USE = 2


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
        super().__init__(segment_type, strict=True)
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
        super().__init__(segment_type, strict=False)
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


def aggregate_optional_score(scores, eps=1e-5):
    """
    Aggregate optional scores.

        - NaNs are filted out
        - for empty score vector, return 1.0
        - if some score is too low (<1e-5), return 0.0
        - otherwise, take harmonic mean of all scores

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#combining-the-scores
    """
    na_scores = scores.isna()
    have_zeros = (scores < eps).any(axis=1)
    aggregated_scores = (~na_scores).sum(axis=1) / (1.0 / scores).sum(axis=1)
    aggregated_scores.loc[have_zeros] = 0
    aggregated_scores.fillna(1.0, inplace=True)
    return aggregated_scores


def _scale_bias(scale, kind):
    if kind == UNIFORM_BIAS:
        return 1
    elif kind == LINEAR_BIAS:
        if scale > 1.0:
            return 1.0 / scale
        else:
            return scale
    elif kind == GAUSSIAN_BIAS:
        gaussian = norm(loc=1, scale=0.25)
        norm_factor = gaussian.pdf(1)
        return gaussian.pdf(scale) / norm_factor
    else:
        raise ValueError(
            f"The kind must be one of [{LINEAR_BIAS}, {UNIFORM_BIAS}, {GAUSSIAN_BIAS}]"
        )


def score_morphologies(
    position, rules, params, scale=1.0, segment_type=None,
    bias_kind=LINEAR_BIAS, optional_scores_process=COMPUTE_OPTIONAL_SCORES.COMPUTE_AND_USE
):
    """
    Calculate placement score for a batch of annotated morphologies.

    Args:
        position: layer profile (a mapping with 'y' + '<layer>_[0|1]' values)
        rules: dict of placement rules functors
        params: pandas DataFrame with morphology annotations
        scale: scale factor along Y-axis
        segment_type: if specified, check only corresponding rules ('axon' or 'dendrite')
        bias_kind: kind of bias for the scale (can be uniform, linear or gaussian)
        optional_scores_process: should be an instance of COMPUTE_OPTIONAL_SCORES enum that defines
            whether optional scores are computed and used or not.

    Returns:
        pandas DataFrame with aggregated scores;
            rows correspond to morphologies,
            columns correspond to strict / optional / total scores.

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#combining-the-scores
    """
    result = pd.DataFrame(index=params.index)
    strict, optional = [], []
    for rule_id, rule in rules.items():
        if (segment_type is not None) and (rule.segment_type != segment_type):
            continue
        annotation = params[rule_id].dropna()
        result[rule_id] = rule(position=position, annotation=annotation, scale=scale)
        if rule.strict:
            strict.append(rule_id)
        else:
            optional.append(rule_id)
    result['strict'] = aggregate_strict_score(result[strict])
    result['total'] = result['strict'] * _scale_bias(scale, kind=bias_kind)
    if optional_scores_process != COMPUTE_OPTIONAL_SCORES.DO_NOT_COMPUTE:
        result['optional'] = aggregate_optional_score(result[optional])
        if optional_scores_process == COMPUTE_OPTIONAL_SCORES.COMPUTE_AND_USE:
            result['total'] *= result['optional']
    return result


def _export_scores(
    scores_output_file: str,
    scores: pd.DataFrame,
    choice: int,
    weights: pd.Series,
    w_sum: float,
    with_scales: bool,
) -> None:
    """Export the scores to the given file."""
    scores["weight"] = weights
    scores["chosen"] = False
    if choice is not None:
        scores.loc[choice, "chosen"] = True
    scores["probability"] = weights / w_sum
    if with_scales:
        scores.rename_axis(index=["morphology", "scale"], inplace=True)
        scores.reset_index(level=1, inplace=True)
    scores.to_csv(scores_output_file, index_label="morphology")


# pylint: disable=too-many-arguments
def choose_morphology(
    position,
    rules,
    params,
    alpha=1.0,
    scales=None,
    segment_type=None,
    scores_output_file=None,
    bias_kind=LINEAR_BIAS,
    with_optional_scores=True,
):
    """
    Choose morphology from a list of annotated morphologies.

    Args:
        position: layer profile (a mapping with 'y' + '<layer>_[0|1]' values)
        rules: dict of placement rules functors
        params: pandas DataFrame with morphology annotations
        alpha: exponential factor for scores
        scales: list of scales to choose from
        segment_type: if specified, check only corresponding rules ('axon' or 'dendrite')
        scores_output_file: if set to a path, scores are exported to this path
        bias_kind: kind of bias for the scale (can be linear or gaussian)
        with_optional_scores: if set to False, the optional rules are ignored for choice

    Returns:
        Morphology picked at random with scores ** alpha as probability weights
        (`None` if all the morphologies score 0).
    """
    if with_optional_scores:
        compute_optional_scores = COMPUTE_OPTIONAL_SCORES.COMPUTE_AND_USE
    elif scores_output_file is not None:
        compute_optional_scores = COMPUTE_OPTIONAL_SCORES.COMPUTE_ONLY
    else:
        compute_optional_scores = COMPUTE_OPTIONAL_SCORES.DO_NOT_COMPUTE

    if scales is None:
        scores = score_morphologies(
            position, rules, params, segment_type=segment_type, bias_kind=bias_kind,
            optional_scores_process=compute_optional_scores
        )
    else:
        scores = {}
        for scale in scales:
            scores[scale] = score_morphologies(
                position, rules, params, scale=scale, segment_type=segment_type,
                bias_kind=bias_kind, optional_scores_process=compute_optional_scores
            )
        scores = pd.concat(scores).swaplevel()
    weights = scores['total'].values ** alpha
    w_sum = np.sum(weights)

    if np.isclose(w_sum, 0.0):
        choice = None
    else:
        choice = np.random.choice(scores.index.values, p=weights / w_sum)

    if scores_output_file is not None:
        _export_scores(scores_output_file, scores, choice, weights, w_sum, scales is not None)

    return choice
