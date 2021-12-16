from pathlib import Path

import pytest
import yaml

import placement_algorithm.validation as test_module


@pytest.fixture
def config():
    path = Path(__file__).parent / "data/rotations.yaml"
    with path.open(encoding="utf-8") as fd:
        return yaml.safe_load(fd)


@pytest.fixture
def schema():
    path = Path(__file__).parent.parent / "placement_algorithm/data/schemas/rotations.yaml"
    with path.open(encoding="utf-8") as fd:
        return yaml.safe_load(fd)


def test_validate_config_valid(config, schema):
    test_module.validate_config(config, schema=schema)


@pytest.mark.parametrize(
    "key,value",
    [
        ("distr", ["normal", {"mean": 0.0, "sd": 1.0}, "additional_item"]),
        ("distr", 123),
        ("query", 456),
        ("axis", "w"),
        ("invalid_key", "value"),
    ],
)
def test_validate_config_invalid_rule(config, schema, caplog, key, value):
    config["rotations"][0][key] = value
    with pytest.raises(test_module.ValidationError):
        test_module.validate_config(config, schema=schema)
    assert "Invalid configuration:\n1: Failed validating root.rotations.0" in caplog.text


@pytest.mark.parametrize(
    "key,value",
    [
        ("distr", ["normal", {"mean": 0.0, "sd": 1.0}, "additional_item"]),
        ("distr", 123),
        ("query", 456),
        ("axis", "w"),
        ("invalid_key", "value"),
    ],
)
def test_validate_config_invalid_default_rotation(config, schema, caplog, key, value):
    config["default_rotation"][key] = value
    with pytest.raises(test_module.ValidationError):
        test_module.validate_config(config, schema=schema)
    assert "Invalid configuration:\n1: Failed validating root.default_rotation" in caplog.text


def test_validate_config_empty(schema, caplog):
    with pytest.raises(test_module.ValidationError):
        test_module.validate_config(config={}, schema=schema)
    assert (
        "Invalid configuration:\n1: Failed validating root: {} does not have enough properties"
        in caplog.text
    )


def test_validate_config_none(schema, caplog):
    with pytest.raises(test_module.ValidationError):
        test_module.validate_config(config=None, schema=schema)
    assert "The configuration cannot be empty." in caplog.text
