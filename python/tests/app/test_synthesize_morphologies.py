from pathlib import Path
from tempfile import TemporaryDirectory

from nose.tools import assert_equal

from mock import MagicMock, patch
from placement_algorithm.app import utils
from placement_algorithm.app.synthesize_morphologies import Worker

from .mock import AtlasMock, CellCollectionMock

DATA = Path(__file__).parent.parent.parent.parent / 'tests' / 'data'


@patch('placement_algorithm.app.synthesize_morphologies.Atlas.open',
       MagicMock(return_value=AtlasMock()))
@patch('placement_algorithm.app.synthesize_morphologies.CellCollection.load_mvd3',
       MagicMock(return_value=CellCollectionMock()))
def test_run():
    args = MagicMock()
    args.tmd_distributions = DATA / 'distributions.json'
    args.tmd_parameters = DATA / 'parameters.json'
    args.morph_axon = None
    args.seed = 0

    with TemporaryDirectory('test-run-synthesis') as folder:
        folder = Path(folder)
        morph_writer = utils.MorphWriter(folder, ['h5', 'swc', 'asc'])
        morph_writer.prepare(num_files=12, max_files_per_dir=257)

        worker = Worker(morph_writer)
        worker.setup(args)
        worker(gid=0)
        assert_equal(set(folder.rglob('*')),
                     {folder / '02583f52ff47b88961e4216e2972ee8c.h5',
                      folder / '02583f52ff47b88961e4216e2972ee8c.swc',
                      folder / '02583f52ff47b88961e4216e2972ee8c.asc'})
