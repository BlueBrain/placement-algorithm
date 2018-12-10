"""
MorphIO-based utilities for building / mutating morphologies.
"""

from morphio import SectionType


def find_axon(morph):
    """ Find and return axon neurite in a given morphology object. """
    axons = [s for s in morph.root_sections if s.type == SectionType.axon]
    assert len(axons) == 1
    return axons[0]


def remove_axon(morph):
    """ Remove axon from a given mutable morphology object. """
    # pylint: disable=unused-argument
    # TODO
    pass


def apply_rotation(obj, rotation):
    """ Apply rotation to a morphology or neurite. """
    # pylint: disable=unused-argument
    # TODO
    pass


def graft_axon(morph, axon):
    """ Add `axon` neurite to a given mutable morphology object. """
    # pylint: disable=unused-argument
    # TODO
    pass
