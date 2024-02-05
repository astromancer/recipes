
# std
import contextlib as ctx
import multiprocessing as mp

# third-party
import numpy as np
from tqdm import tqdm
from loguru import logger
from joblib import Parallel, delayed

# local
import motley
from recipes.io import load_memmap_nans

# relative
from .. import api
from ..config import ConfigNode
from ..flow.contexts import ContextStack
from ..logging import LoggingMixin, TqdmLogAdapter, TqdmStreamAdapter
from .joblib import initialized


# ---------------------------------------------------------------------------- #
CONFIG = ConfigNode.load_module(__file__)

# stylize progressbar
prg = CONFIG.progress
prg['bar_format'] = motley.stylize(prg.bar_format)
del prg


# ---------------------------------------------------------------------------- #
# Multiprocessing

# default lock - does nothing
memory_lock = ctx.nullcontext()


def set_lock(mem_lock, tqdm_lock):
    """
    Initialize each process with a global variable lock.
    """
    global memory_lock
    memory_lock = mem_lock
    tqdm.set_lock(tqdm_lock)


# ---------------------------------------------------------------------------- #

class Executor(LoggingMixin):

    def __init__(self, jobname='', backend='multiprocessing', **kws):
        self.backend = str(backend)
        self.jobname = jobname
        self.results = None
        self.kws = kws

    def init_memory(self, shape, overwrite=False):
        """
        Initialize shared memory synchronised access wrappers. Should only be
        run in the main process.

        Parameters
        ----------
        n:
            number of frames
        overwrite

        Returns
        -------

        """
        self.results = load_memmap_nans(shape=shape, overwrite=overwrite)

    def __call__(self, data, indices=None):
        """
        Track the shift of the image frame from initial coordinates

        Parameters
        ----------
        image
        mask

        Returns
        -------

        """

        if self.results is None:
            raise FileNotFoundError('Initialize memory first by calling the '
                                    '`init_memory` method.')

        if data.ndim == 2:
            data = [data]

        return self.run(data, indices)

    def __str__(self):
        name = type(self).__name__
        if (m := self.results) is None:
            return f'{name}(0/0)'
        return f'{name}({self.completed.sum()} / {len(m)})'

    __repr__ = __str__

    # ------------------------------------------------------------------------ #
    @property
    def completed(self):
        # boolean array flags True if frame has any measurement(s)
        return ~np.isnan(self.results).all(
            tuple({*range(self.results.ndim)} - {0})
        )

    @api.synonyms({'n_jobs': 'njobs'})
    def run(self, data, indices=None, njobs=-1, progress_bar=True, **kws):
        """
        Start a worker pool of source trackers. The workload will be split into
        chunks of size ``

        Parameters
        ----------
        data : array-like
            Image stack.
        indices : Iterable, optional
            Indices of frames to compute, the default None, runs through all the
            data.
        njobs : int, optional
            Number of concurrent woorker processes to launch, by default -1

        progress_bar : bool, optional
            _description_, by default True

        Raises
        ------
        FileNotFoundError
            If memory has not been initialized prior to calling this method.
        """
        # preliminary checks
        if self.results is None:
            raise FileNotFoundError('Initialize memory first by calling the '
                                    '`init_memory` method.')

        if indices is None:
            indices, = np.where(~self.completed)

        indices = list(indices)
        if len(indices) == 0:
            self.logger.info('All data have been processed. To force a rerun, '
                             'you may do >>> tracker.completed[:] = 0')
            return

        if njobs in (-1, None):
            njobs = mp.cpu_count()

        # main compute
        self.main(data, indices, njobs, progress_bar, **kws)

    def main(self, data, indices, njobs,  progress_bar, **kws):

        # setup compute context
        worker, context = self.setup(njobs, progress_bar, **self.kws)

        logger.remove()
        logger.add(TqdmStreamAdapter(), colorize=True, enqueue=True)

        # execute
        with context as compute:
            compute(worker(data, *args, **kws) for args in
                    self.get_workload(indices, progress_bar))

        # self.logger.debug('With {} backend, pickle serialization took: {:.3f}s.',
        #              backend, time.time() - t_start)
        self.logger.debug('Task {} complete. Returning results.', self.jobname)
        return self.results

    def setup(self, njobs, progress_bar, **kws):

        # setup compute context
        if njobs == 1:
            return self.compute, ctx.nullcontext(list)

        # locks for managing output contention
        tqdm.set_lock(mp.RLock())
        memory_lock = mp.Lock()

        # NOTE: object serialization is about x100-150 times faster with
        # "multiprocessing" backend. ~0.1s vs 10s for "loky".
        worker = delayed(self.compute)
        executor = Parallel(njobs, self.backend, **kws)
        context = ContextStack(
            initialized(executor, set_lock, (memory_lock, tqdm.get_lock()))
        )
        # Adapt logging for progressbar
        if progress_bar:
            # These catch the print statements
            context.add(TqdmLogAdapter())

        return worker, context

    def get_workload(self, indices, progress_bar=True):
        # workload iterable with progressbar if required
        workload = zip(indices, )
        return tqdm(workload, self.jobname,
                    initial=self.completed.sum(), total=len(indices),
                    disable=not progress_bar, **CONFIG.progress)

    def compute(self, data, index, **kws):
        # measure
        self.results[index] = self._compute(data, **kws)

    def _compute(self, *data, **kws):
        raise NotImplementedError()
