#!/usr/bin/env python2

import os
import sys
import argparse
import logging

import lxml.etree
import numpy as np
import pandas as pd


L = logging.getLogger(__name__)


def y_absolute(y_rel, candidate):
    """ Given candidate layer profile, convert (layer, fraction) pair to absolute Y value. """
    layer, fraction = y_rel
    y0 = candidate[layer + "_0"]
    y1 = candidate[layer + "_1"]
    return (1.0 - fraction) * y0 + fraction * y1


class YBelowRule(object):
    """ Check that 'y' does not exceed given limit. """
    def __init__(self, y_rel, tolerance):
        self.y_rel = y_rel
        self.tolerance = tolerance

    @classmethod
    def from_attr(cls, attr):
        y_rel = attr['y_layer'], float(attr['y_fraction'])
        tolerance = float(attr.get('tolerance', 30.0))
        return cls(y_rel=y_rel, tolerance=tolerance)

    def __call__(self, candidate, annotation):
        """ score = 1.0 - clip((y_candidate - y_annotation) / tolerance, 0.0, 1.0). """
        y_limit = y_absolute(self.y_rel, candidate)
        delta = (candidate['y'] + float(annotation['y_max'])) - y_limit
        if delta < 0.0:
            score = 1.0
        elif delta > self.tolerance:
            score = 0.0
        else:
            score = 1.0 - delta / self.tolerance
        return score

    @property
    def strict(self):
        return True


class YRangeOverlapRule(object):
    """ Check that '[y1; y2]' falls within given interval. """
    def __init__(self, y_rel_min, y_rel_max):
        self.y_rel_min = y_rel_min
        self.y_rel_max = y_rel_max

    @classmethod
    def from_attr(cls, attr):
        y_rel_min = attr['y_min_layer'], float(attr['y_min_fraction'])
        y_rel_max = attr['y_max_layer'], float(attr['y_max_fraction'])
        return cls(y_rel_min=y_rel_min, y_rel_max=y_rel_max)

    def __call__(self, candidate, annotation):
        """ score = overlap(candidate, annotation) / max_possible_overlap(candidate, annotation). """
        y1 = y_absolute(self.y_rel_min, candidate)
        y2 = y_absolute(self.y_rel_max, candidate)
        y1c = candidate['y'] + float(annotation['y_min'])
        y2c = candidate['y'] + float(annotation['y_max'])
        y1o, y2o = max(y1, y1c), min(y2, y2c)
        if y1o > y2o:
            score = 0.0
        else:
            score = (y2o - y1o) / min(y2 - y1, y2c - y1c)
        return score

    @property
    def strict(self):
        return False


DISPATCH_RULE = {
    'below': YBelowRule,
    'region_target': YRangeOverlapRule,
}


def generalized_mean(x, p):
    assert not np.isclose(p, 0.0)
    return np.power(np.mean(np.power(x, p)), 1.0 / p)


def aggregate_optional_scores(scores, p):
    scores = np.array(scores)
    if len(scores) > 0:
        return generalized_mean(1.0 + scores, p) - 1.0
    else:
        return 0.0


def aggregate_strict_scores(scores):
    if len(scores) > 0:
        return np.min(scores)
    else:
        return 1.0


def score_candidate(candidate, annotation, rules, p=1.0):
    strict_scores, optional_scores = [], []
    for item in annotation:
        if item['rule'] not in rules:
            L.warning("Ignoring rule %s", item['rule'])
            continue
        rule = rules[item['rule']]
        score = rule(candidate=candidate, annotation=item)
        L.debug("%s: score=%.3f (%s)", candidate['id'], score, item['rule'])
        if rule.strict:
            strict_scores.append(score)
        else:
            optional_scores.append(score)

    strict_score = aggregate_strict_scores(strict_scores)
    optional_score = aggregate_optional_scores(optional_scores, p)
    L.info("%s: strict=%.3f; optional=%.3f", candidate['id'], strict_score, optional_score)
    return strict_score * (1.0 + optional_score) / 2


def load_rules(filepath):
    """ Parse XML with placement rules. """
    result = {}
    etree = lxml.etree.parse(filepath)
    for elem in etree.findall('*/rule'):
        attr = elem.attrib
        rule_id = attr['id']
        if rule_id in result:
            raise ValueError("Duplicate rule id: '%s'" % rule_id)
        rule_type = attr['type']
        if rule_type in DISPATCH_RULE:
            result[rule_id] = DISPATCH_RULE[rule_type].from_attr(attr)
        else:
            L.debug("Unknown placement rule type: %s", rule_type)
    return result


def load_annotation(filepath):
    """ Parse XML with morphology annotations. """
    etree = lxml.etree.parse(filepath)
    return [elem.attrib for elem in etree.findall('placement')]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Score placement candidates.")
    parser.add_argument(
        "-r", "--rules",
        help="Path to placement rules",
        required=True
    )
    parser.add_argument(
        "-a", "--annotations",
        help="Path to annotations folder",
        required=True
    )
    parser.add_argument(
        "-l", "--layers",
        required=True,
        help="Layer names as they appear in layer profile (comma-separated)"
    )
    parser.add_argument(
        "-p", "--p-order",
        type=float,
        default=1.0,
        help="p-order for optional scores generalized mean (default: %(default)s)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action='count',
        help="Log verbosity level",
        default=0
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARN)
    L.setLevel({
        0: logging.WARN,
        1: logging.INFO,
        2: logging.DEBUG,
    }[args.verbose])

    rules = load_rules(args.rules)

    columns = ['morph', 'id', 'y'] + sum([['%s_0' % layer, '%s_1' % layer] for layer in args.layers.split(",")], [])
    candidates = pd.read_csv(sys.stdin, sep=r'\s+', names=columns)
    for _, candidate in candidates.iterrows():
        annotation_path = os.path.join(args.annotations, candidate.morph + ".xml")
        try:
            annotation = load_annotation(annotation_path)
        except IOError:
            L.warning("No annotation found for '%s', skipping", candidate.morph)
            continue
        score = score_candidate(candidate, annotation, rules, p=args.p_order)
        print candidate.morph, candidate.id, "%.3f" % score

