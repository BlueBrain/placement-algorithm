from unittest.mock import MagicMock, call, patch

import numpy as np
import pandas as pd

from numpy.testing import assert_array_almost_equal
from scipy.spatial.transform import Rotation

import placement_algorithm.rotation as test_module


def _get_atlas_orientations():
    return np.array(
        [
            # no rotation
            [
                [1, 0, 0],
                [0, 1, 0],
                [0, 0, 1],
            ],
            # x-axis, 60-degrees
            [
                [1, 0, 0],
                [0, 0.5, -0.866025404],
                [0, 0.866025404, 0.5],
            ],
            # x-axis, 90-degrees
            [
                [1, 0, 0],
                [0, 0, -1],
                [0, 1, 0],
            ],
            # y-axis, 60-degrees
            [
                [0.5, 0, 0.866025404],
                [0, 1, 0],
                [-0.866025404, 0, 0.5],
            ],
            # y-axis, 90-degrees
            [
                [0, 0, 1],
                [0, 1, 0],
                [-1, 0, 0],
            ],
            # z-axis, 60-degrees
            [
                [0.5, -0.866025404, 0],
                [0.866025404, 0.5, 0],
                [0, 0, 1],
            ],
            # z-axis, 90-degrees
            [
                [0, -1, 0],
                [1, 0, 0],
                [0, 0, 1],
            ],
            # generic rotation
            [
                [0.95268223, 0.27585598, 0.12767161],
                [-0.10635323, -0.0909688, 0.99015841],
                [0.28475525, -0.95688461, -0.05732618],
            ],
        ],
        dtype="float64",
    )


def _get_properties():
    df = pd.DataFrame(
        np.array(
            [
                ["SLM", "SLM", "SLM_PPA", "INH", "INT", "bAC", 0],
                ["SLM", "SLM", "SLM_PPA", "EXC", "INT", "cAC", 1],
                ["SO", "SO", "SO_BP", "INH", "INT", "cACpyr", 2],
                ["SO", "SO", "SO_BP", "EXC", "INT", "cNAC", 3],
                ["SP", "SP", "SP_PC", "INH", "PYR", "bAC", 4],
                ["SP", "SP", "SP_PC", "EXC", "PYR", "cAC", 5],
                ["SR", "SR", "SR_SCA", "INH", "PYR", "cACpyr", 6],
                ["SR", "SR", "SR_SCA", "EXC", "PYR", "cNAC", 7],
            ],
        ),
        # `num` is not a real property, but it's used to select rows with a query during tests
        columns=["layer", "region", "mtype", "synapse_class", "morph_class", "etype", "num"],
    )
    return df.astype({"num": int})


def _parse_distr_side_effect(name):
    """Return a mock of a SciPy random variable, providing only the `rvs` method."""
    return {
        "distr_2a": MagicMock(rvs=lambda size: np.array([np.pi / 2, np.pi / 4])),
        "distr_2b": MagicMock(rvs=lambda size: np.array([np.pi / 5, -np.pi / 7])),
        "distr_2c": MagicMock(rvs=lambda size: np.array([np.pi / 11, np.pi / 13])),
        "distr_3a": MagicMock(rvs=lambda size: np.array([np.pi, -np.pi / 2, -np.pi / 4])),
        "distr_3b": MagicMock(rvs=lambda size: np.array([-np.pi / 3, np.pi / 3, -np.pi / 6])),
    }[name]


def _cells_mock():
    # simplified mock of voxcell.CellCollection
    cells = MagicMock()
    cells.properties = _get_properties()
    cells.__len__ = lambda self: len(self.properties)
    return cells


def test_assign_orientations_without_random_rotation():
    cells = _cells_mock()
    atlas_orientations = _get_atlas_orientations()

    test_module.assign_orientations(cells, orientations=atlas_orientations, config={})

    assert_array_almost_equal(cells.orientations, atlas_orientations)


@patch(test_module.__name__ + ".np.random.uniform")
def test_assign_orientations_with_uniform_rotation(uniform_mock):
    cells = _cells_mock()
    atlas_orientations = _get_atlas_orientations()
    angles = np.array([(2 * i / len(cells) - 1) * np.pi for i in range(len(cells))])
    uniform_mock.return_value = angles
    expected_orientations = np.array(
        [
            atlas_orientations[i] @ Rotation.from_euler("y", a).as_matrix()
            for i, a in enumerate(angles)
        ]
    )

    test_module.assign_orientations(cells, orientations=atlas_orientations, config=None)

    uniform_mock.assert_called_once_with(-np.pi, np.pi, size=len(cells))
    assert_array_almost_equal(cells.orientations, expected_orientations)


@patch(test_module.__name__ + ".parse_distr", side_effect=_parse_distr_side_effect)
def test_assign_orientations_with_custom_rotation_right_handed(parse_distr_mock):
    cells = _cells_mock()
    atlas_orientations = _get_atlas_orientations()
    q1 = "num == [4, 5]"
    q2 = "num == [0, 3, 7]"
    rotations = {
        "rotations": [
            {"query": q1, "rotations_by_axis": [{"axis": "y", "distr": "distr_2a"}]},
            {"query": q2, "rotations_by_axis": [{"axis": "y", "distr": "distr_3a"}]},
        ]
    }
    expected_orientations = np.array(
        [
            atlas_orientations[0] @ Rotation.from_euler("y", np.pi).as_matrix(),
            atlas_orientations[1],
            atlas_orientations[2],
            atlas_orientations[3] @ Rotation.from_euler("y", -np.pi / 2).as_matrix(),
            atlas_orientations[4] @ Rotation.from_euler("y", np.pi / 2).as_matrix(),
            atlas_orientations[5] @ Rotation.from_euler("y", np.pi / 4).as_matrix(),
            atlas_orientations[6],
            atlas_orientations[7] @ Rotation.from_euler("y", -np.pi / 4).as_matrix(),
        ]
    )

    test_module.assign_orientations(cells, orientations=atlas_orientations, config=rotations)

    assert parse_distr_mock.call_args_list == [call("distr_3a"), call("distr_2a")]
    assert_array_almost_equal(cells.orientations, expected_orientations)


@patch(test_module.__name__ + ".parse_distr", side_effect=_parse_distr_side_effect)
def test_assign_orientations_with_custom_rotation_and_overlapping(parse_distr_mock):
    # should give the same result as test_assign_orientations_with_custom_rotation_right_handed
    cells = _cells_mock()
    atlas_orientations = _get_atlas_orientations()
    q1 = "num == [0, 4, 5, 7]"  # overlapping ids 0, 7 should be ignored
    q2 = "num == [0, 3, 7]"
    rotations = {
        "rotations": [
            {"query": q1, "rotations_by_axis": [{"axis": "y", "distr": "distr_2a"}]},
            {"query": q2, "rotations_by_axis": [{"axis": "y", "distr": "distr_3a"}]},
        ]
    }
    expected_orientations = np.array(
        [
            atlas_orientations[0] @ Rotation.from_euler("y", np.pi).as_matrix(),
            atlas_orientations[1],
            atlas_orientations[2],
            atlas_orientations[3] @ Rotation.from_euler("y", -np.pi / 2).as_matrix(),
            atlas_orientations[4] @ Rotation.from_euler("y", np.pi / 2).as_matrix(),
            atlas_orientations[5] @ Rotation.from_euler("y", np.pi / 4).as_matrix(),
            atlas_orientations[6],
            atlas_orientations[7] @ Rotation.from_euler("y", -np.pi / 4).as_matrix(),
        ]
    )

    test_module.assign_orientations(cells, orientations=atlas_orientations, config=rotations)

    assert parse_distr_mock.call_args_list == [call("distr_3a"), call("distr_2a")]
    assert_array_almost_equal(cells.orientations, expected_orientations)


@patch(test_module.__name__ + ".parse_distr", side_effect=_parse_distr_side_effect)
def test_assign_orientations_with_custom_rotation_and_default_fallback(parse_distr_mock):
    cells = _cells_mock()
    atlas_orientations = _get_atlas_orientations()
    q1 = "num == [4, 5]"
    q2 = "num == [0, 3, 7]"
    rotations = {
        "rotations": [
            {"query": q1, "rotations_by_axis": [{"axis": "y", "distr": "distr_2a"}]},
            {"query": q2, "rotations_by_axis": [{"axis": "y", "distr": "distr_3a"}]},
        ],
        "default_rotation": {"rotations_by_axis": [{"axis": "y", "distr": "distr_3b"}]},
    }
    expected_orientations = np.array(
        [
            atlas_orientations[0] @ Rotation.from_euler("y", np.pi).as_matrix(),
            atlas_orientations[1] @ Rotation.from_euler("y", -np.pi / 3).as_matrix(),
            atlas_orientations[2] @ Rotation.from_euler("y", np.pi / 3).as_matrix(),
            atlas_orientations[3] @ Rotation.from_euler("y", -np.pi / 2).as_matrix(),
            atlas_orientations[4] @ Rotation.from_euler("y", np.pi / 2).as_matrix(),
            atlas_orientations[5] @ Rotation.from_euler("y", np.pi / 4).as_matrix(),
            atlas_orientations[6] @ Rotation.from_euler("y", -np.pi / 6).as_matrix(),
            atlas_orientations[7] @ Rotation.from_euler("y", -np.pi / 4).as_matrix(),
        ]
    )

    test_module.assign_orientations(cells, orientations=atlas_orientations, config=rotations)

    assert parse_distr_mock.call_args_list == [call("distr_3a"), call("distr_2a"), call("distr_3b")]
    assert_array_almost_equal(cells.orientations, expected_orientations)


@patch(test_module.__name__ + ".parse_distr", side_effect=_parse_distr_side_effect)
def test_assign_orientations_with_custom_rotation_and_different_axis(parse_distr_mock):
    cells = _cells_mock()
    atlas_orientations = _get_atlas_orientations()
    q1 = "num == [4, 5]"
    q2 = "num == [0, 3, 7]"
    rotations = {
        "rotations": [
            {"query": q1, "rotations_by_axis": [{"axis": "x", "distr": "distr_2a"}]},
            {"query": q2, "rotations_by_axis": [{"axis": "z", "distr": "distr_3a"}]},
        ],
    }
    expected_orientations = np.array(
        [
            atlas_orientations[0] @ Rotation.from_euler("z", np.pi).as_matrix(),
            atlas_orientations[1],
            atlas_orientations[2],
            atlas_orientations[3] @ Rotation.from_euler("z", -np.pi / 2).as_matrix(),
            atlas_orientations[4] @ Rotation.from_euler("x", np.pi / 2).as_matrix(),
            atlas_orientations[5] @ Rotation.from_euler("x", np.pi / 4).as_matrix(),
            atlas_orientations[6],
            atlas_orientations[7] @ Rotation.from_euler("z", -np.pi / 4).as_matrix(),
        ]
    )

    test_module.assign_orientations(cells, orientations=atlas_orientations, config=rotations)

    assert parse_distr_mock.call_args_list == [call("distr_3a"), call("distr_2a")]
    assert_array_almost_equal(cells.orientations, expected_orientations)


@patch(test_module.__name__ + ".parse_distr", side_effect=_parse_distr_side_effect)
def test_assign_orientations_with_custom_rotation_and_multiple_axis(parse_distr_mock):
    cells = _cells_mock()
    atlas_orientations = _get_atlas_orientations()
    q1 = "num == [4, 5]"
    rotations = {
        "rotations": [
            {
                "query": q1,
                "rotations_by_axis": [
                    {"axis": "y", "distr": "distr_2a"},
                    {"axis": "x", "distr": "distr_2b"},
                    {"axis": "z", "distr": "distr_2c"},
                ],
            },
        ],
    }
    expected_orientations = np.array(
        [
            atlas_orientations[0],
            atlas_orientations[1],
            atlas_orientations[2],
            atlas_orientations[3],
            atlas_orientations[4]
            @ Rotation.from_euler("z", np.pi / 11).as_matrix()
            @ Rotation.from_euler("x", np.pi / 5).as_matrix()
            @ Rotation.from_euler("y", np.pi / 2).as_matrix(),
            atlas_orientations[5]
            @ Rotation.from_euler("z", np.pi / 13).as_matrix()
            @ Rotation.from_euler("x", -np.pi / 7).as_matrix()
            @ Rotation.from_euler("y", np.pi / 4).as_matrix(),
            atlas_orientations[6],
            atlas_orientations[7],
        ]
    )

    test_module.assign_orientations(cells, orientations=atlas_orientations, config=rotations)

    assert parse_distr_mock.call_args_list == [call("distr_2a"), call("distr_2b"), call("distr_2c")]
    assert_array_almost_equal(cells.orientations, expected_orientations)


@patch(test_module.__name__ + ".parse_distr", side_effect=_parse_distr_side_effect)
def test_assign_orientations_with_empty_selection(parse_distr_mock):
    cells = _cells_mock()
    atlas_orientations = _get_atlas_orientations()
    q1 = "num == [1004, 1005]"  # nonexistent nums -> empty selection
    q2 = "num == [0, 3, 7]"
    rotations = {
        "rotations": [
            {"query": q1, "rotations_by_axis": [{"axis": "y", "distr": "distr_2a"}]},
            {"query": q2, "rotations_by_axis": [{"axis": "y", "distr": "distr_3a"}]},
        ]
    }
    expected_orientations = np.array(
        [
            atlas_orientations[0] @ Rotation.from_euler("y", np.pi).as_matrix(),
            atlas_orientations[1],
            atlas_orientations[2],
            atlas_orientations[3] @ Rotation.from_euler("y", -np.pi / 2).as_matrix(),
            atlas_orientations[4],
            atlas_orientations[5],
            atlas_orientations[6],
            atlas_orientations[7] @ Rotation.from_euler("y", -np.pi / 4).as_matrix(),
        ]
    )

    test_module.assign_orientations(cells, orientations=atlas_orientations, config=rotations)

    assert parse_distr_mock.call_args_list == [call("distr_3a")]  # distr_2a is not called
    assert_array_almost_equal(cells.orientations, expected_orientations)


@patch(test_module.__name__ + ".parse_distr", side_effect=_parse_distr_side_effect)
def test_assign_orientations_with_null_distr(parse_distr_mock):
    cells = _cells_mock()
    atlas_orientations = _get_atlas_orientations()
    q1 = "num == [4, 5]"  # not rotated
    q2 = "num == [0, 3, 7]"
    rotations = {
        "rotations": [
            {"query": q1, "rotations_by_axis": None},
            {"query": q2, "rotations_by_axis": [{"axis": "y", "distr": "distr_3a"}]},
        ],
        "default_rotation": {"rotations_by_axis": [{"axis": "y", "distr": "distr_3b"}]},
    }
    expected_orientations = np.array(
        [
            atlas_orientations[0] @ Rotation.from_euler("y", np.pi).as_matrix(),
            atlas_orientations[1] @ Rotation.from_euler("y", -np.pi / 3).as_matrix(),
            atlas_orientations[2] @ Rotation.from_euler("y", np.pi / 3).as_matrix(),
            atlas_orientations[3] @ Rotation.from_euler("y", -np.pi / 2).as_matrix(),
            atlas_orientations[4],
            atlas_orientations[5],
            atlas_orientations[6] @ Rotation.from_euler("y", -np.pi / 6).as_matrix(),
            atlas_orientations[7] @ Rotation.from_euler("y", -np.pi / 4).as_matrix(),
        ]
    )

    test_module.assign_orientations(cells, orientations=atlas_orientations, config=rotations)

    assert parse_distr_mock.call_args_list == [call("distr_3a"), call("distr_3b")]
    assert_array_almost_equal(cells.orientations, expected_orientations)
