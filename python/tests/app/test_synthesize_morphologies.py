'''
This test is being run through mpiexec, not nosetests
mpiexec -n 4 python test_synthesize_morphologies.py

The test function should NOT have *test* in the name, or nosetests
will run it.
'''
import shutil
from pathlib import Path
import yaml

from numpy.testing import assert_allclose
from nose.tools import assert_equal, ok_
from mock import MagicMock, patch
from morph_tool.utils import iter_morphology_files

import placement_algorithm.app.synthesize_morphologies as tested
from placement_algorithm.app.mpi_app import _run, MASTER_RANK
from atlas_mock import CellCollectionMock, small_O1
from mpi4py import MPI

PATH = Path(__file__).parent
DATA = Path(PATH, '../../../tests/data').resolve()

@patch('placement_algorithm.app.utils.CellCollection.load_mvd3',
       MagicMock(return_value=CellCollectionMock()))
def run_mpi():
    tmp_folder = Path('/tmp/test-run-synthesis')

    args = MagicMock()
    args.tmd_distributions = DATA / 'distributions.json'
    args.tmd_parameters = DATA / 'parameters.json'
    args.morph_axon = None
    args.seed = 0
    args.num_files = 12
    args.max_files_per_dir = 256
    args.overwrite = True
    args.out_morph_ext = ['h5', 'swc', 'asc']
    args.out_morph_dir = tmp_folder
    args.out_apical = tmp_folder / 'apical.yaml'
    args.atlas = str(tmp_folder)
    args.no_mpi = False

    is_master = MPI.COMM_WORLD.Get_rank() == MASTER_RANK

    if not is_master:
        _run(tested.Master, args)
        return

    tmp_folder.mkdir(exist_ok=True)

    try:
        small_O1(tmp_folder)
        _run(tested.Master, args)
        assert_equal(len(list(iter_morphology_files(tmp_folder))), 36)
        ok_(args.out_apical.exists())
        with args.out_apical.open() as f, (DATA / 'apical.yaml').open() as expected:
            apical_points = yaml.load(f, Loader=yaml.FullLoader)
            expected_apical_points = yaml.load(expected, Loader=yaml.FullLoader)
        assert_equal(apical_points.keys(), expected_apical_points.keys())
        for k in apical_points.keys():
            assert_allclose(apical_points[k], expected_apical_points[k])
    finally:
        shutil.rmtree(tmp_folder)


if __name__ == '__main__':
    run_mpi()
