
# std
import contextlib as ctx
import multiprocessing as mp
from collections import abc

# third-party
import numpy as np
from tqdm import tqdm
from loguru import logger
from joblib import Parallel, delayed

# local
import motley

# relative
from .. import pprint as pp
from ..io import load_memmap
from ..config import ConfigNode
from ..oo.slots import SlotHelper
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

class Executor(LoggingMixin, SlotHelper):

    __slots__ = ('jobname', 'backend', 'results', 'config')

    def __init__(self, jobname=None, backend='multiprocessing', **config):
        self.jobname = type(self).__name__ if jobname is None else str(jobname)
        self.backend = str(backend)
        self.results = None
        self.config = config

    def init_memory(self, shape, masked=False, loc=None, overwrite=False):
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
        self.results = load_memmap(loc, shape, fill=np.nan, overwrite=overwrite)
        self.mask = None
        if masked:
            self.mask = load_memmap(loc, shape, bool, True, overwrite)

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

    # ------------------------------------------------------------------------ #
    @property
    def completed(self):
        # boolean array flags True if frame has any measurement(s)
        return ~np.isnan(self.results).all(
            tuple({*range(self.results.ndim)} - {0})
        )

    # @api.synonyms({'n_jobs': 'njobs'})
    def run(self, data=None, indices=None, njobs=-1, progress_bar=True, *args, **kws):
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

        self.logger.debug('indices = {}', indices)

        if self.results is None:
            raise FileNotFoundError('Initialize memory first by calling the '
                                    '`init_memory` method.')

        if njobs in (-1, None):
            njobs = mp.cpu_count()

        # main compute
        self.logger.debug('indices = {}', indices)
        self.main(data, indices, njobs, progress_bar, *args, **kws)

    def main(self, data, indices, njobs, progress_bar, *extra_args, **kws):

        # setup compute context
        worker, context = self.setup(njobs, progress_bar, **self.config)

        logger.remove()
        logger.add(TqdmStreamAdapter(), colorize=True, enqueue=True)

        # execute
        with context as compute:
            self.logger.debug('indices = {}', indices)
            compute(worker(*args, *extra_args, **kws) for args in
                    self.get_workload(data, indices, progress_bar))

        # self.logger.debug('With {} backend, pickle serialization took: {:.3f}s.',
        #              backend, time.time() - t_start)
        self.logger.debug('Task {} complete. Returning results.', self.jobname)
        return self.results

    def setup(self, njobs, progress_bar, **kws):

        self.logger.opt(lazy=True).debug(
            'Compute setup: {}', lambda: pp.pformat(locals(), ignore='self')
        )

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

    def get_workload(self, data, indices, progress_bar=True):
        # workload iterable with progressbar if required

        done = self.completed
        if indices is None:
            indices, = np.where(~done)

        indices = list(indices)
        self.logger.debug('indices = {}', indices)

        if len(indices) == 0:
            self.logger.info('All data have been processed. To force a rerun, '
                             'you may reset the memory\n'
                             ' >>> exec.init_memory(..., overwrite=True)')

            return ()

        #
        self.logger.debug('Creating workload: {}', data, indices)

        if isinstance(data, (np.ndarray, list)):
            workload = ((data[i], i) for i in indices)
        elif isinstance(data, abc.Iterable):
            workload = zip(data, indices)
        else:
            raise TypeError(f'Cannot create workload from data of type {type(data)}.')

        return tqdm(workload, self.jobname,
                    initial=done.sum(), total=len(done),
                    disable=not progress_bar, **CONFIG.progress)

    def compute(self, data, index, **kws):

        # compute
        self.results[index] = result = self._compute(data, **kws)

        # handle masked
        if self.mask is not None and np.ma.is_masked(result):
            self.mask[index] = result.mask

    def _compute(self, *data, **kws):
        raise NotImplementedError()
