"""Utilities for random sampling."""
import json

import scipy.stats


class Distributions:
    """Distributions wrapper."""

    def get(self, name, params):
        """Return a distribution object from scipy.stats."""
        try:
            func = getattr(self, f"_get_{name}")
        except AttributeError:
            func = getattr(scipy.stats, name)
        return func(**params)

    @staticmethod
    def _get_norm(**params):
        loc = _get_value(params, ("mean", "loc"))
        scale = _get_value(params, ("sd", "scale"))
        return scipy.stats.norm(loc=loc, scale=scale)

    @staticmethod
    def _get_truncnorm(**params):
        loc = _get_value(params, ("mean", "loc"))
        scale = _get_value(params, ("sd", "scale"))
        a = _get_value(params, ("low", "a"))
        b = _get_value(params, ("high", "b"))
        return scipy.stats.truncnorm(a=a, b=b, loc=loc, scale=scale)

    @staticmethod
    def _get_uniform(**params):
        loc = params.get("loc")
        scale = params.get("scale")
        if loc is None or scale is None:
            a = params["low"]
            b = params["high"]
            loc = min(a, b)
            scale = max(a, b) - loc
        return scipy.stats.uniform(loc=loc, scale=scale)

    @staticmethod
    def _get_vonmises(**params):
        loc = _get_value(params, ("mu", "loc"))
        kappa = params["kappa"]
        scale = params.get("scale", 1)  # optional scale
        return scipy.stats.vonmises(kappa=kappa, loc=loc, scale=scale)


def _get_value(mapping, keys):
    """Return the value of the first key from `keys` found in `mapping`."""
    for k in keys:
        if k in mapping:
            return mapping[k]
    raise KeyError(keys)


def parse_distr(value):
    """Convert distribution config into `scipy.stats` distribution object.

    Args:
        value: it can be either
            - a tuple (<distribution name>, <distribution parameters>)
            - a string with JSON serialization of such a tuple

    See also:
    https://docs.scipy.org/doc/scipy/reference/stats.html
    https://bbpteam.epfl.ch/project/spaces/display/BBPNSE/Defining+distributions+in+config+files

    Originally based on brainbuilder.utils.random.parse_distr.
    """
    if isinstance(value, str):
        value = json.loads(value)
    func, params = value
    return Distributions().get(func, params)
