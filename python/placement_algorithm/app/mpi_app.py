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
        pass

    @abc.abstractproperty
    def logger(self):
        """ Application logger. """
        pass

    @abc.abstractmethod
    def finalize(self, result):
        """
        Finalize master work (e.g, write result to file).

        Args:
            result: {task_id -> *} dictionary (e.g, morphology name per GID)
        """
        pass


class WorkerApp(object):
    """ Worker app interface. """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def setup(self, args):
        """ Initialize worker task. """
        pass

    @abc.abstractmethod
    def __call__(self):
        """
        Process task with the given task ID.

        Returns:
            (task_id, result) tuple.
        """
        pass


def run_master(master, args, COMM):
    """ To-be-executed on master node (MPI_RANK == 0). """
    import numpy as np
    from tqdm import tqdm

    worker = master.setup(args)

    COMM.bcast(worker, root=MASTER_RANK)

    # Some tasks take longer to process than the others.
    # Distribute them randomly across workers to amortize that.
    task_ids = np.random.permutation(master.task_ids)

    worker_count = COMM.Get_size() - 1
    master.logger.info("Distributing %d tasks across %d worker(s)...", len(task_ids), worker_count)

    for rank, chunk in enumerate(np.array_split(task_ids, worker_count), 1):
        COMM.send(chunk, dest=rank)

    master.logger.info("Processing tasks...")
    result = dict([
        COMM.recv()
        for _ in tqdm(range(len(task_ids)))
    ])

    master.finalize(result)

    master.logger.info("Done!")


def run_worker(args, COMM):
    """ To-be-executed on worker nodes (MPI_RANK > 0). """
    worker = COMM.bcast(None, root=MASTER_RANK)
    worker.setup(args)
    task_ids = COMM.recv(source=MASTER_RANK)
    for _id in task_ids:
        COMM.send((_id, worker(_id)), dest=MASTER_RANK)


def run(App):
    """ Launch MPI-based Master / Worker application. """
    from mpi4py import MPI  # pylint: disable=import-error

    COMM = MPI.COMM_WORLD
    if COMM.Get_size() < 2:
        raise RuntimeError(
            "MPI environment should contain at least two nodes;\n"
            "rank 0 serves as the coordinator, rank N > 0 -- as task workers.\n"
        )

    args = App.parse_args()
    if COMM.Get_rank() == MASTER_RANK:
        run_master(App(), args, COMM)
    else:
        run_worker(args, COMM)
