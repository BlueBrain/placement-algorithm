'''
This test is being run through mpiexec, not nosetests
mpiexec -n 4 python test_synthesize_morphologies.py

The test function should NOT have *test* in the name, or nosetests
will run it.
'''
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from nose.tools import assert_equal, ok_
from mock import MagicMock, patch
from morph_tool.utils import iter_morphology_files

import placement_algorithm.app.synthesize_morphologies as test_module
from placement_algorithm.app.mpi_app import _run, MASTER_RANK
from atlas_mock import AtlasMock, CellCollectionMock
from mpi4py import MPI

PATH = Path(__file__).parent
DATA = Path(PATH, '../../../tests/data').resolve()

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
    args.out_morph_ext = ['swc', 'asc']
    args.out_morph_dir = tmp_folder
    args.out_apical = tmp_folder / 'apical.json'

    is_master = MPI.COMM_WORLD.Get_rank() == MASTER_RANK

    if not is_master:
        _run(test_module.Master, args)
        return

    tmp_folder.mkdir(exist_ok=True)

    try:
        _run(test_module.Master, args)
        assert_equal(len(list(iter_morphology_files(tmp_folder))), 24)
        ok_(args.out_apical.exists())
    finally:
        shutil.rmtree(tmp_folder)




if __name__ == '__main__':
    run_mpi()
