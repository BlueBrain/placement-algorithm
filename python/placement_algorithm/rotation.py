"""Utilities for rotation."""
import numpy as np

from scipy.spatial.transform import Rotation

from placement_algorithm.logger import LOGGER
from placement_algorithm.random import parse_distr
from placement_algorithm.utils import filter_ids


def _rotate_as_matrix(orientations, angles, axes):
    """Combine the rotations of the given angles/axes with the given orientations matrices.

    The rotation around the axes is applied before the rotation given by the orientations matrices.

    Args:
        orientations: (N, 3, 3) array of rotation matrices.
        angles: (N, W) array of angles in radians.
        axes: string of W axes for rotations, where each axis is one of 'x', 'y', 'z'.

    Returns:
        The resulting array of rotation matrices.
    """
    r1 = Rotation.from_euler(axes, angles)
    r2 = Rotation.from_matrix(orientations)
    return (r2 * r1).as_matrix()


def _rotate_selection(orientations, modified, idx, rotations_by_axis, query=None):
    """Apply a rotation to a selection of cells identified by idx, unless already modified.

    The arrays `orientations` and `modified` are modified inplace.

    Args:
        orientations: (N, 3, 3) array of rotation matrices.
        modified: (N,) boolean array indicating if a cell has been already modified.
        idx: numeric (not boolean) index of unique cells to be rotated.
        rotations_by_axis (list): optional list of dictionaries of rotations, containing:
            distr: a pair of distribution name and dict of parameters, for instance:
                ('uniform', {'low': -np.pi, 'high': +np.pi})
            axis: one of ('x', 'y', 'z').
        query: query used to determine the cells to be rotated, only for logging purposes.
    """
    assert np.issubdtype(idx.dtype, np.integer), "The index type must be integer"
    # get the values of idx that have not been touched yet
    untouched_idx = np.setdiff1d(idx, np.where(modified), assume_unique=True)
    modified[untouched_idx] = True
    LOGGER.info(
        "Processing %s cells and ignoring %s cells already considered, %s %s: %s",
        len(untouched_idx),
        len(idx) - len(untouched_idx),
        f"selected with query {query!r}" if query else "selected by default",
        f"with {len(rotations_by_axis or [])} random rotation(s)",
        rotations_by_axis,
    )
    # apply the random rotation only if needed
    if rotations_by_axis and len(untouched_idx) > 0:
        rows = len(orientations[untouched_idx])
        cols = len(rotations_by_axis)
        axes = ""
        angles = np.empty((rows, cols))
        for i, rot in enumerate(rotations_by_axis):
            assert rot["axis"] in ("x", "y", "z"), "Invalid axis"
            axes += rot["axis"]
            angles[:, i] = parse_distr(rot["distr"]).rvs(size=rows)
        orientations[untouched_idx] = _rotate_as_matrix(
            orientations[untouched_idx], angles=angles, axes=axes
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
        cells.orientations = _rotate_as_matrix(orientations, angles=angles, axes="y")
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
            rotations_by_axis=rotation["rotations_by_axis"],
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
            rotations_by_axis=rotation["rotations_by_axis"],
        )
    cells.orientations = orientations
