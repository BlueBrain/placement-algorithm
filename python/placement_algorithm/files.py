"""
Module for parsing files used by placement algorithm:
 - placement rules
 - morphology annotations
 - (ext)neuronDB.dat
"""

import lxml.etree
import numpy as np
import pandas as pd

from placement_algorithm.algorithm import BelowRule, RegionTargetRule, RegionOccupyRule
from placement_algorithm.exceptions import PlacementError
from placement_algorithm.logger import LOGGER


DISPATCH_RULES = {
    'below': BelowRule,
    'region_target': RegionTargetRule,
    'region_occupy': RegionOccupyRule,
}


def _parse_rule_set(group):
    result = {}
    for elem in group.findall('rule'):
        rule_id = elem.attrib['id']
        if rule_id in result:
            raise PlacementError(f"Duplicate rule '{rule_id}'")
        rule_type = elem.attrib['type']
        if rule_type in DISPATCH_RULES:
            result[rule_id] = DISPATCH_RULES[rule_type].from_xml(elem)
        else:
            LOGGER.warning("Unknown placement rule type: %s, skipping", rule_type)
    return result


def _parse_rules(etree):
    """ Parse XML with placement rules. """
    elems = etree.findall('global_rule_set')
    if len(elems) < 1:
        common_rules = {}
    elif len(elems) == 1:
        common_rules = _parse_rule_set(elems[0])
    elif len(elems) > 1:
        raise PlacementError("Duplicate <global_rule_set>")

    mtype_rules = {}
    for elem in etree.findall('mtype_rule_set'):
        for mtype in elem.attrib['mtype'].split("|"):
            if mtype in mtype_rules:
                raise PlacementError(f"Duplicate <mtype_rule_set> for mtype '{mtype}'")
            mtype_rules[mtype] = _parse_rule_set(elem)
            mtype_rules[mtype].update(common_rules)

    return common_rules, mtype_rules


def _collect_layer_names(etree):
    result = set()
    for elem in etree.iter('rule'):
        for name in ('y_layer', 'y_min_layer', 'y_max_layer'):
            attr = elem.attrib.get(name)
            if attr is not None:
                result.add(attr)
    return result


class PlacementRules:
    """
    Access to placement rules XML

    See also:
    https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html#placement-rules
    """
    def __init__(self, filepath):
        etree = lxml.etree.parse(filepath)
        self.common_rules, self.mtype_rules = _parse_rules(etree)
        self.layer_names = _collect_layer_names(etree)

    def bind(self, annotations, mtype):
        """
        Bind 'raw' annotations to `mtype` rules.

        Args:
            annotations: {morphology -> {rule -> {param -> value}}} dict

        Returns:
            (rules, params) pair, where `rules` is a dict
            with rules applicable for `mtype`;
            and `params` - pandas DataFrame with annotations
            (rows correspond to morphologies; columns - to (rule, param))
        """
        rules = self.mtype_rules.get(mtype, self.common_rules)
        rule_params = {}
        for morph, annotation in annotations.items():
            row = {
                (rule_id, param): np.nan
                for rule_id, rule in rules.items()
                for param in rule.ANNOTATION_PARAMS
            }
            for rule_id, params in annotation.items():
                if rule_id in rules:
                    for param, value in params.items():
                        if (rule_id, param) not in row:
                            continue
                        row[(rule_id, param)] = float(value)
                elif rule_id == "ScaleBias":
                    # temporary fix to suppress excessive warnings with existing annotations
                    pass
                else:
                    LOGGER.warning("Unexpected rule ID: '%s' (%s)", rule_id, morph)
            rule_params[morph] = row
        return (
            rules,
            pd.DataFrame(rule_params).transpose()
        )


def parse_annotations(filepath):
    """ Parse XML with morphology annotations. """
    etree = lxml.etree.parse(filepath)
    result = {}
    for elem in etree.findall('placement'):
        attr = dict(elem.attrib)
        rule_id = attr.pop('rule')
        if rule_id in result:
            raise PlacementError(f"Duplicate annotation for rule '{rule_id}'")
        result[rule_id] = attr
    return result


def parse_morphdb(filepath):
    """ Parse (ext)neuronDB.dat file. """
    columns = ['morphology', 'layer', 'mtype']
    first_row = pd.read_csv(filepath, sep=r'\s+', header=None, nrows=1)
    if first_row.shape[1] > 3:
        columns.append('etype')
    return pd.read_csv(
        filepath, sep=r'\s+', names=columns, usecols=columns, na_filter=False
    )
