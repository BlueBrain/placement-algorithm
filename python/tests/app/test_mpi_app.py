import mock
import nose.tools as nt

from mock import patch, Mock

import placement_algorithm.app.mpi_app as test_module

import sys
sys.modules['mpi4py'] = Mock()


@patch('mpi4py.MPI.COMM_WORLD')
def test_run_master(COMM):
    master = Mock()
    master.task_ids = [1, 2]
    COMM.Get_size.return_value = 3
    COMM.Get_rank.return_value = 0
    COMM.recv.side_effect = [(1, 11), (2, 22)]
    test_module.run(Mock(return_value=master))
    master.assert_has_calls([
        mock.call.setup(mock.ANY),
        mock.call.finalize({1: 11, 2: 22})
    ])


@patch('mpi4py.MPI.COMM_WORLD')
def test_run_worker(COMM):
    worker = Mock()
    COMM.Get_size.return_value = 3
    COMM.Get_rank.return_value = 1
    COMM.bcast.return_value = worker
    COMM.recv.return_value = [42, 43]
    app = Mock()
    app.parse_args.return_value = 'args'
    test_module.run(app)
    COMM.bcast.assert_called_once_with(None, root=0)
    COMM.recv.assert_called_once_with(source=0)
    worker.assert_has_calls([
        mock.call.setup('args'),
        mock.call(42),
        mock.call(43),
    ])


@patch('mpi4py.MPI.COMM_WORLD')
def test_run_invalid_allocation(COMM):
    COMM.Get_size.return_value = 1
    nt.assert_raises(
        RuntimeError,
        test_module.run, mock.MagicMock()
    )
