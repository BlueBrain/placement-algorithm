import mock
from nose.tools import assert_dict_equal, assert_raises
from pathlib import Path
from tempfile import TemporaryDirectory
import yaml

from mock import patch, Mock

import placement_algorithm.app.mpi_app as test_module

import sys
sys.modules['mpi4py'] = Mock()


class DummyParser:
    no_mpi = False
    out = None

class DummyWorkerApp(test_module.WorkerApp):
    def setup(self, args):
        pass
    def __call__(self, gid):
        return 11 * gid

def get_dummy_app(args):
    '''Returns a class whose static method pass_args return value can be specified

    We want to run some unit test with different arguments, but since pass_args is
    a static method we can't reuse the same class. This will generate a different class everytime
    '''
    class DummyMasterApp(test_module.MasterApp):
        @staticmethod
        def parse_args():
            return args

        @property
        def task_ids(self):
            return [1, 2]

        def finalize(self, result):
            '''double result values'''
            with DummyMasterApp.parse_args().out.open('w') as f:
                yaml.dump(result, f)

        def setup(self, args):
            return DummyWorkerApp()
    return DummyMasterApp

def test_run_master_no_mpi():
    with TemporaryDirectory() as folder:
        args = DummyParser()
        args.out = Path(folder, 'result.yaml')
        args.no_mpi = True
        test_module.run(get_dummy_app(args))
        with args.out.open() as f:
            assert_dict_equal(yaml.load(f, Loader=yaml.FullLoader),
                              {1: 11, 2: 22})


@patch('mpi4py.MPI.COMM_WORLD')
def test_run_master(COMM):
    COMM.Get_size.return_value = 3
    COMM.Get_rank.return_value = 0
    COMM.recv.side_effect = [(1, 11), (2, 22)]

    with TemporaryDirectory() as folder:
        args = DummyParser()
        args.out = Path(folder, 'result.yaml')
        test_module.run(get_dummy_app(args))
        with args.out.open() as f:
            assert_dict_equal(yaml.load(f, Loader=yaml.FullLoader),
                              {1: 11, 2: 22})


@patch('mpi4py.MPI.COMM_WORLD')
def test_run_worker(COMM):
    worker = Mock()
    COMM.Get_size.return_value = 3
    COMM.Get_rank.return_value = 1
    COMM.bcast.return_value = worker
    COMM.recv.return_value = [42, 43]
    args = DummyParser()
    app = get_dummy_app(args)()
    test_module.run(app)
    COMM.bcast.assert_called_once_with(None, root=0)
    COMM.recv.assert_called_once_with(source=0)
    worker.assert_has_calls([
        mock.call.setup(mock.ANY),
        mock.call(42),
        mock.call(43),
    ])

@patch('mpi4py.MPI.COMM_WORLD')
def test_run_invalid_allocation(COMM):
    COMM.Get_size.return_value = 1
    args = DummyParser()
    assert_raises(
        RuntimeError,
        test_module.run, get_dummy_app(args)
    )
