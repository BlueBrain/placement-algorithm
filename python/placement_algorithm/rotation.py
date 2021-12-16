"""Utilities for rotation."""
import numpy as np

from scipy.spatial.transform import Rotation

from placement_algorithm.logger import LOGGER
from placement_algorithm.random import parse_distr
from placement_algorithm.utils import filter_ids


def _rotate_as_matrix(orientations, angles, axis):
    """Combine the rotations of the given angles/axis with the given orientations matrices.

    The rotation around the axis is applied before the rotation given by the orientations matrices.

    Args:
        orientations: (N, 3, 3) array of rotation matrices.
        angles: (N,) array of angles in radians.
        axis: one of ('x', 'y', 'z').

    Returns:
        The resulting array of rotation matrices.
    """
    r1 = Rotation.from_euler(axis, angles)
    r2 = Rotation.from_matrix(orientations)
    return (r2 * r1).as_matrix()


def _rotate_selection(orientations, modified, idx, distr, axis, query=None):
    """Apply a rotation to a selection of cells identified by idx, unless already modified.

    The arrays `orientations` and `modified` are modified inplace.

    Args:
        orientations: (N, 3, 3) array of rotation matrices.
        modified: (N,) boolean array indicating if a cell has been already modified.
        idx: numeric (not boolean) index of unique cells to be rotated.
        distr: a pair of distribution name and dict of parameters, for instance:
            ('uniform', {'low': -np.pi, 'high': +np.pi})
            It can be None, in which case the rotation is not applied.
        axis: one of ('x', 'y', 'z'), or None if distr is None.
        query: query used to determine the cells to be rotated, only for logging purposes.
    """
    assert np.issubdtype(idx.dtype, np.integer), "The index type must be integer"
    # get the values of idx that have not been touched yet
    untouched_idx = np.setdiff1d(idx, np.where(modified), assume_unique=True)
    modified[untouched_idx] = True
    LOGGER.info(
        "Processing %s cells and ignoring %s cells already considered, %s %s %s",
        len(untouched_idx),
        len(idx) - len(untouched_idx),
        f"selected with query {query!r}" if query else "selected by default",
        f"with random rotation and distribution {distr!r}" if distr else "without random rotation",
        f"around axis {axis}" if distr else "",
    )
    # apply the random rotation only if needed
    if distr and len(untouched_idx) > 0:
        if axis not in {"x", "y", "z"}:
            raise ValueError(f"Invalid axis: {axis!r}")
        angles = parse_distr(distr).rvs(size=len(orientations[untouched_idx]))
        orientations[untouched_idx] = _rotate_as_matrix(
            orientations[untouched_idx], angles=angles, axis=axis
        )


def assign_orientations(cells, orientations, config):
    """
    Randomly rotate and assign cell orientations to CellCollection based on atlas orientations.

    Args:
        cells: CellCollection to be augmented.
        orientations: (N, 3, 3) array of rotation matrices.
        config (dict|None): configuration defining the additional random rotations to be applied.
            If None, apply a random rotation around Y-axis for backward compatibility.
    """
    if config is None:
        LOGGER.info("Morphologies are going to be rotated around Y-axis with uniform distribution")
        angles = np.random.uniform(-np.pi, np.pi, size=len(cells))
        cells.orientations = _rotate_as_matrix(orientations, angles=angles, axis="y")
        return
    LOGGER.info(
        "Morphologies are going to be rotated according to the configuration. "
        "If multiple rules affect the same cells, the rules defined later prevail over the former. "
        "Note that the rotation rules are processed and logged in reverse order."
    )
    # the cell properties index is expected to be ordered, without any gap, and starting from 0
    assert np.all(cells.properties.index == np.arange(len(cells)))
    # boolean array of modified cells
    modified = np.full(len(cells), fill_value=False, dtype=bool)
    # Apply rotations in reverse order so that the last rules have precedence in case of overlap,
    # without the need to keep a copy of the initial orientations.
    # NOTE: if it will be needed to support multiple rotations of the same cells around different
    #       axis, then the logic should be changed to process the rotations in the same order.
    for rotation in reversed(config.get("rotations", [])):
        idx = filter_ids(cells.properties, query=rotation["query"])
        _rotate_selection(
            orientations=orientations,
            modified=modified,
            idx=idx,
            distr=rotation["distr"],
            axis=rotation.get("axis"),
            query=rotation["query"],
        )
    # Change all the remaining unmodified cells if a default rotation is defined
    rotation = config.get("default_rotation")
    if rotation:
        idx = np.where(~modified)[0]  # 1D array
        _rotate_selection(
            orientations=orientations,
            modified=modified,
            idx=idx,
            distr=rotation["distr"],
            axis=rotation.get("axis"),
        )
    cells.orientations = orientations
