#!/usr/bin/env python2

import os
import sys
import copy
import argparse
import logging

import lxml.etree
import numpy as np
import pandas as pd


# Score to give to rules with missing annotations
MISSING_RULE_SCORE = 0.1

# Known annotations to ignore
IGNORED_RULES = {
    'ScaleBias'
}


L = logging.getLogger(__name__)


def y_absolute(y_rel, candidate):
    """ Given candidate layer profile, convert (layer, fraction) pair to absolute Y value. """
    layer, fraction = y_rel
    y0 = candidate[layer + "_0"]
    y1 = candidate[layer + "_1"]
    return (1.0 - fraction) * y0 + fraction * y1


class YBelowRule(object):
    """ Check that 'y' does not exceed given limit. """
    def __init__(self, _id, y_rel, tolerance):
        self.id = _id
        self.y_rel = y_rel
        self.tolerance = tolerance

    @classmethod
    def from_attr(cls, attr):
        y_rel = attr['y_layer'], float(attr['y_fraction'])
        tolerance = float(attr.get('tolerance', 30.0))
        return cls(attr['id'], y_rel=y_rel, tolerance=tolerance)

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
    def __init__(self, _id, y_rel_min, y_rel_max):
        self.id = _id
        self.y_rel_min = y_rel_min
        self.y_rel_max = y_rel_max

    @classmethod
    def from_attr(cls, attr):
        y_rel_min = attr['y_min_layer'], float(attr['y_min_fraction'])
        y_rel_max = attr['y_max_layer'], float(attr['y_max_fraction'])
        return cls(attr['id'], y_rel_min=y_rel_min, y_rel_max=y_rel_max)

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
        return 1.0


def aggregate_strict_scores(scores):
    if len(scores) > 0:
        return np.min(scores)
    else:
        return 1.0


def score_candidate(candidate, morph_rules, p=1.0):
    log_tag = "(%s; %s)" % (candidate['id'], candidate['morph'])
    strict_scores, optional_scores = [], []

    for rule, annotation in morph_rules:
        if annotation is None:
            score = MISSING_RULE_SCORE
        else:
            score = rule(candidate=candidate, annotation=annotation)
        L.debug("%s: score=%.3f (%s)", log_tag, score, rule.id)
        if rule.strict:
            strict_scores.append(score)
        else:
            optional_scores.append(score)

    strict_score = aggregate_strict_scores(strict_scores)
    optional_score = aggregate_optional_scores(optional_scores, p)
    L.info("%s: strict=%.3f; optional=%.3f", log_tag, strict_score, optional_score)
    return strict_score * optional_score


def parse_rule_set(group):
    result = {}
    for elem in group.findall('rule'):
        attr = elem.attrib
        rule_id = attr['id']
        if rule_id in result:
            raise RuntimeError("Duplicate rule '%s'", rule_id)
        rule_type = attr['type']
        if rule_type in DISPATCH_RULE:
            result[rule_id] = DISPATCH_RULE[rule_type].from_attr(attr)
        else:
            L.warning("Unknown placement rule type: %s, skipping", rule_type)
    return result


def load_rules(filepath):
    """ Parse XML with placement rules. """
    etree = lxml.etree.parse(filepath)

    elems = etree.findall('/global_rule_set')
    if len(elems) < 1:
        common_rules = {}
    elif len(elems) == 1:
        common_rules = parse_rule_set(elems[0])
    elif len(elems) > 1:
        raise RuntimeError("Duplicate <global_rule_set>")

    mtype_rules = {}
    for elem in etree.findall('/mtype_rule_set'):
        mtype = elem.attrib['mtype']
        if mtype in mtype_rules:
            raise RuntimeError("Duplicate <mtype_rule_set> for mtype '%s'", mtype)
        mtype_rules[mtype] = parse_rule_set(elem)

    return common_rules, mtype_rules


def load_annotation(annotation_dir, morphology):
    """ Parse XML with morphology annotations. """
    filepath = os.path.join(annotation_dir, morphology + ".xml")
    etree = lxml.etree.parse(filepath)
    return [elem.attrib for elem in etree.findall('/placement')]


class PlacementRules(object):
    def __init__(self, filepath):
        self.common_rules, self.mtype_rules = load_rules(filepath)

    def bind(self, annotation, mtype):
        """ Bind annotation to placement rules. """
        common_rules = copy.copy(self.common_rules)
        mtype_rules = copy.copy(self.mtype_rules.get(mtype, {}))

        result = []
        for item in annotation:
            params = copy.copy(item)
            rule_id = params.pop('rule')
            if rule_id in mtype_rules:
                rule = mtype_rules.pop(rule_id)
            elif rule_id in common_rules:
                rule = common_rules.pop(rule_id)
            elif rule_id in IGNORED_RULES:
                continue
            else:
                L.warning("Unknown rule: '%s', skipping", rule_id)
                continue
            result.append((rule, params))

        for rule_id, rule in common_rules.iteritems():
            L.warning("Missing 'rule' annotation: '%s'", rule_id)
            result.append((rule, None))

        for rule_id, rule in mtype_rules.iteritems():
            L.warning("Missing rule annotation: '%s'", rule_id)
            result.append((rule, None))

        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Score placement candidates")
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
        "--profile",
        default=None,
        help="Layer thickness ratio to use for 'short' candidate form (total thickness only)"
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

    rules = PlacementRules(args.rules)

    layers = args.layers.split(",")

    base_columns = ['mtype', 'morph', 'id', 'y']
    if args.profile:
        profile = np.array(args.profile.split(","), dtype=float)
        profile/= np.sum(profile)
        candidates = pd.read_csv(sys.stdin, sep=r'\s+', names=base_columns + ['h'])
        y0, y1 = None, 0
        for layer, dy in zip(layers, profile):
            y0 = y1
            y1 = y0 + dy
            candidates['%s_0' % layer] = y0 * candidates['h']
            candidates['%s_1' % layer] = y1 * candidates['h']
        del candidates['h']
    else:
        layer_columns = sum([['%s_0' % layer, '%s_1' % layer] for layer in layers], [])
        candidates = pd.read_csv(sys.stdin, sep=r'\s+', names=base_columns + layer_columns)

    for _, candidate in candidates.iterrows():
        try:
            annotation = load_annotation(args.annotations, candidate.morph)
        except IOError:
            L.warning("No annotation found for '%s', skipping", candidate.morph)
            continue
        morph_rules = rules.bind(annotation, candidate.mtype)
        score = score_candidate(candidate, morph_rules, p=args.p_order)
        print candidate.morph, candidate.id, "%.3f" % score

