'''
This test is being run through mpiexec, not nosetests
mpiexec -n 4 python test_synthesize_morphologies.py

The test function should NOT have *test* in the name, or nosetests
will run it.
'''
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from numpy.testing import assert_array_equal
from nose.tools import assert_equal, ok_, assert_raises
from mock import MagicMock, patch
from morph_tool.utils import iter_morphology_files

import placement_algorithm.app.synthesize_morphologies as tested
from placement_algorithm.app.mpi_app import _run, MASTER_RANK
from atlas_mock import AtlasMock, CellCollectionMock
from mpi4py import MPI

PATH = Path(__file__).parent
DATA = Path(PATH, '../../../tests/data').resolve()


def test_get_NEURON_apical_sections():
    assert_array_equal(tested.get_NEURON_apical_sections(DATA / 'simple.asc', []),
                       [])
    assert_array_equal(tested.get_NEURON_apical_sections(DATA / 'simple.asc', [None]),
                       [])
    assert_array_equal(tested.get_NEURON_apical_sections(DATA / 'apical_test.swc',
                                                         [None, [-2, 28, 0]]),
                       [2])

def test_fail_if_only_h5_output_ext():
    args = MagicMock()
    args.out_morph_ext = ['h5']
    assert_raises(Exception, tested.Master().setup, args)

@patch('placement_algorithm.app.synthesize_morphologies.Atlas.open',
       MagicMock(return_value=AtlasMock()))
@patch('placement_algorithm.app.synthesize_morphologies.CellCollection.load_mvd3',
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
    args.out_apical = tmp_folder / 'apical.json'

    is_master = MPI.COMM_WORLD.Get_rank() == MASTER_RANK

    if not is_master:
        _run(tested.Master, args)
        return

    tmp_folder.mkdir(exist_ok=True)

    try:
        _run(tested.Master, args)
        assert_equal(len(list(iter_morphology_files(tmp_folder))), 36)
        ok_(args.out_apical.exists())
    finally:
        shutil.rmtree(tmp_folder)


if __name__ == '__main__':
    run_mpi()
