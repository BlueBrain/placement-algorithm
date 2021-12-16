import nose.tools as nt
import numpy as np
from numpy.testing import assert_almost_equal

import placement_algorithm.random as test_module


def rad(angle):
    return angle * np.pi / 180


def test_parse_distr_uniform():
    np.random.seed(0)
    d = test_module.parse_distr(("uniform", {"low": rad(30), "high": rad(120)}))
    assert_almost_equal(d.rvs(100).mean(), 1.2662616020358175)


def test_parse_distr_norm():
    np.random.seed(0)
    d = test_module.parse_distr(("norm", {"mean": rad(30), "sd": 0.5}))
    assert_almost_equal(d.rvs(100).mean(), 0.5535027833655414)


def test_parse_distr_truncnorm():
    np.random.seed(0)
    d = test_module.parse_distr(
        ("truncnorm", {"mean": rad(60), "sd": 0.5, "low": rad(30), "high": rad(120)})
    )
    assert_almost_equal(d.rvs(100).mean(), 1.5665960539972894)


def test_parse_distr_vonmises():
    np.random.seed(0)
    d = test_module.parse_distr(("vonmises", {"mu": rad(30), "kappa": 2}))
    assert_almost_equal(d.rvs(100).mean(), 0.6079840662814191)


def test_parse_distr_scipy_fallback():
    np.random.seed(0)
    d = test_module.parse_distr(("gamma", {"a": 1}))
    assert_almost_equal(d.rvs(100).mean(), 0.9186484131475078)


def test_parse_distr_string():
    np.random.seed(0)
    d = test_module.parse_distr('["uniform", {"low": 1, "high": 2}]')
    assert_almost_equal(d.rvs(100).mean(), 1.472793839512518)


def test_parse_distr_raises():
    nt.assert_raises(KeyError, test_module.parse_distr, ("norm", {"loc": 2}))
    nt.assert_raises(AttributeError, test_module.parse_distr, ("foo", None))
