""" Exceptions used throughout package. """


class PlacementError(Exception):
    """ Base class for 'placement-algorithm' exceptions. """


class SkipSynthesisError(Exception):
    '''An exception thrown when the morphology synthesis must be skipped'''
