"""
Simplistic MPI-based master-workers architecture.

It is based on two classes, for master and workers logic accordingly.

Master node (MPI_RANK == 0):
    - initial setup (e.g, parsing config files)
    - instantiating worker instance
    - broadcasting worker instance to worker nodes
    - distributing tasks across workers
    - collecting results from workers
    - final steps after parallel part (e.g., writing result to file)

Worker nodes (MPI_RANK > 0):
    - instantiate worker instance broadcasted from master
    - set it up (e.g., load atlas data into memory)
    - receive task IDs from master
    - for each task ID, send result to master
"""

import abc
import sys

from placement_algorithm.logger import LOGGER


MASTER_RANK = 0


class MasterApp(object):
    """ Master app interface. """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def setup(self, args):
        """
        Initialize master task.

        Returns:
            An instance of Worker to be spawned on worker nodes.
        """

    @abc.abstractmethod
    def finalize(self, result):
        """
        Finalize master work (e.g, write result to file).

        Args:
            result: {task_id -> *} dictionary (e.g, morphology name per GID)
        """


class WorkerApp(object):
    """ Worker app interface. """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def setup(self, args):
        """ Initialize worker task. """

    @abc.abstractmethod
    def __call__(self):
        """
        Process task with the given task ID.

        Returns:
            (task_id, result) tuple.
        """


def run_master(master, args, COMM):
    """ To-be-executed on master node (MPI_RANK == 0). """
    import numpy as np
    from tqdm import tqdm

    worker = master.setup(args)

    COMM.bcast(worker, root=MASTER_RANK)

    # Some tasks take longer to process than the others.
    # Distribute them randomly across workers to amortize that.
    # NB: task workers should take into account that task IDs are shuffled;
    # and ensure reproducibility themselves.
    task_ids = np.random.permutation(master.task_ids)

    worker_count = COMM.Get_size() - 1
    LOGGER.info("Distributing %d tasks across %d worker(s)...", len(task_ids), worker_count)

    for rank, chunk in enumerate(np.array_split(task_ids, worker_count), 1):
        COMM.send(chunk, dest=rank)

    LOGGER.info("Processing tasks...")
    result = dict(
        COMM.recv()
        for _ in tqdm(range(len(task_ids)))
    )

    master.finalize(result)

    LOGGER.info("Done!")


def run_worker(args, COMM):
    """ To-be-executed on worker nodes (MPI_RANK > 0). """
    worker = COMM.bcast(None, root=MASTER_RANK)
    worker.setup(args)
    task_ids = COMM.recv(source=MASTER_RANK)
    for _id in task_ids:
        try:
            result = worker(_id)
        except Exception:  # pylint: disable=broad-except
            LOGGER.error("Task #%d failed", _id)
            raise
        COMM.send((_id, result), dest=MASTER_RANK)


def _setup_excepthook(COMM):
    def _mpi_excepthook(*args, **kwargs):
        sys.__excepthook__(*args, **kwargs)
        sys.stdout.flush()
        sys.stderr.flush()
        COMM.Abort(1)
    sys.excepthook = _mpi_excepthook


def run(App):
    """ Launch MPI-based Master / Worker application. """
    args = App.parse_args()
    _run(App, args)


def _run(App, args):
    """ Launch MPI-based Master / Worker application. """
    from mpi4py import MPI  # pylint: disable=import-error

    COMM = MPI.COMM_WORLD
    if COMM.Get_size() < 2:
        raise RuntimeError(
            "MPI environment should contain at least two nodes;\n"
            "rank 0 serves as the coordinator, rank N > 0 -- as task workers.\n"
        )

    _setup_excepthook(COMM)

    if COMM.Get_rank() == MASTER_RANK:
        run_master(App(), args, COMM)
    else:
        run_worker(args, COMM)
