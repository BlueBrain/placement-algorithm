from pathlib import Path

import pandas as pd
import pytest
from numpy.testing import assert_array_equal

import placement_algorithm.utils as test_module


def test_resource_path():
    relative_path = "data/schemas/rotations.yaml"
    result = test_module.resource_path(relative_path)

    assert isinstance(result, Path)
    assert result.is_absolute()
    assert result.is_file()
    assert str(result).endswith(relative_path)


@pytest.mark.parametrize(
    "query,expected",
    [
        # query as str
        ("a == 10", [1000]),
        ("a > 11", [1002, 1003]),
        ("a == 10 & b == 'v0'", [1000]),
        ("a == 10 and b == 'v0'", [1000]),
        ("a == 10 & b == 'v2'", []),
        ("a == 10 | b == 'v2'", [1000, 1002]),
        ("a == [11, 13]", [1001, 1003]),
        ("a in [11, 13]", [1001, 1003]),
        ("b == ['v1', 'v3']", [1001, 1003]),
        ("b in ['v1', 'v3']", [1001, 1003]),
        ("a in [11, 13] & b in ['v1', 'v2']", [1001]),
        # query as dict
        ({"a": 10}, [1000]),
        ({"a": 10, "b": "v0"}, [1000]),
        ({"a": 10, "b": "v2"}, []),
        ({"a": [11, 13]}, [1001, 1003]),
        ({"b": ["v1", "v3"]}, [1001, 1003]),
        ({"a": [11, 13], "b": ["v1", "v2"]}, [1001]),
    ],
)
def test_filter_ids(query, expected):
    df = pd.DataFrame(
        {"a": [10, 11, 12, 13], "b": ["v0", "v1", "v2", "v3"]},
        index=[1000, 1001, 1002, 1003],
    )
    result = test_module.filter_ids(df, query=query)
    assert_array_equal(result, expected)
