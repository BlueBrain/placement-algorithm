import json
import tempfile
from itertools import cycle, islice, repeat
from os.path import join
from subprocess import call

import numpy as np
import pandas as pd
from mock import MagicMock
from voxcell import OrientationField, VoxelData
from voxcell.nexus.voxelbrain import Atlas


def small_O1(folder_path):
    '''Dump a small O1 atlas in folder path'''

    call(['brainbuilder', 'atlases',
          '-n', '1,2,3,4,5,6',
          '-t', '200,100,100,100,100,200',
          '-d', '100',
          '-o', str(folder_path),
          'column',
          '-a', '1000',
    ])


class CellCollectionMock(MagicMock):
    size = 12
    def load_mvd3():
        pass

    @property
    def positions(self):
        mock = MagicMock()
        mock.__getitem__ = MagicMock(return_value=[200, 200, 200])
        return mock

    @property
    def properties(self):
        return pd.DataFrame({'mtype': list(repeat('L2_TPC', self.size)),
                             'morphology': list(islice(cycle(['dend-C250500A-P3_axon-C190898A-P2_-_Scale_x1.000_y1.025_z1.000_-_Clone_2',
                                                              'C240300C1_-_Scale_x1.000_y0.975_z1.000_-_Clone_55',
                                                              'dend-Fluo15_right_axon-Fluo2_right_-_Clone_37']),
                                                       self.size))

        })
