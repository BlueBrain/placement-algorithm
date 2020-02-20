from itertools import islice, cycle, repeat
import numpy as np
import pandas as pd
from voxcell import OrientationField, VoxelData
from voxcell.nexus.voxelbrain import Atlas

from mock import MagicMock

DEFAULT_HIERARCHY = {
    "id": 726,
    "acronym": "S1HL",
    "name": "primary somatosensory cortex, hindlimb region",
    "children": [{
        "id": 1125,
        "acronym": "L1",
        "name": "primary somatosensory cortex, hindlimb region, layer 1"
    }, {
        "id": 1126,
        "acronym": "L2",
        "name": "primary somatosensory cortex, hindlimb region, layer 2"
    }, {
        "id": 1127,
        "acronym": "L3",
        "name": "primary somatosensory cortex, hindlimb region, layer 3"
    }, {
        "id": 1128,
        "acronym": "L4",
        "name": "primary somatosensory cortex, hindlimb region, layer 4"
    }, {
        "id": 1129,
        "acronym": "L5",
        "name": "primary somatosensory cortex, hindlimb region, layer 5"
    }, {
        "id": 1130,
        "acronym": "L6",
        "name": "primary somatosensory cortex, hindlimb region, layer 6"
    }]
}


class AtlasMock(Atlas):
    '''A class to mock voxcell.nexus.voxelbrain.Atlas'''
    @staticmethod
    def open(*args, **kwargs):
        pass

    def __init__(self, hierarchy=None, data=None):
        '''

        Args:
            hierarchy: return value of load_hierarchy
            data: a dict where each value is the return value of load_data(key)
        '''
        self.hierarchy = hierarchy or dict(DEFAULT_HIERARCHY)
        self.data = data or dict()

        if 'orientation' not in self.data:
            self.data['orientation'] = OrientationField(
                np.array([[[[1., 0., 0., 0.]]]]), voxel_dimensions=[10., 10., 10.])

        if 'depth' not in self.data:
            self.data['depth'] = VoxelData(np.array([[[12]]]), voxel_dimensions=[10., 10., 10.])

        for layer in range(1, 7):
            key = 'thickness:L{}'.format(layer)
            if key not in self.data:
                self.data[key] = VoxelData(np.array([[[100 * layer]]]),
                                           voxel_dimensions=[10., 10., 10.])

    def load_data(self, data_type, cls=VoxelData):
        """ Return filepath to `data_type` NRRD. """
        if self.data and data_type in self.data:
            return self.data[data_type]
        else:
            return MagicMock()

    def load_hierarchy(self):
        """ Return filepath to brain region hierarchy JSON. """
        return self.hierarchy


class CellCollectionMock(MagicMock):
    size = 12
    def load_mvd3():
        pass

    @property
    def positions(self):
        mock = MagicMock()
        mock.__getitem__ = MagicMock(return_value=[1, 2, 3])
        return mock

    @property
    def properties(self):
        return pd.DataFrame({'mtype': list(repeat('L2_TPC', self.size)),
                             'morphology': list(islice(cycle(['dend-C250500A-P3_axon-C190898A-P2_-_Scale_x1.000_y1.025_z1.000_-_Clone_2',
                                                              'C240300C1_-_Scale_x1.000_y0.975_z1.000_-_Clone_55',
                                                              'dend-Fluo15_right_axon-Fluo2_right_-_Clone_37']),
                                                       self.size))

        })
