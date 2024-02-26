
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
from ..string import Percentage
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
sync_manager = mp.Manager()

# default lock - does nothing
memory_lock = ctx.nullcontext()


def set_locks(mem_lock, tqdm_lock):
    """
    Initialize each process with a global variable lock.
    """
    global memory_lock
    memory_lock = mem_lock
    tqdm.set_lock(tqdm_lock)


# ---------------------------------------------------------------------------- #
class AbortCompute(Exception):
    pass


class Executor(LoggingMixin, SlotHelper):

    __slots__ = ('jobname', 'backend', 'config', 'results', 'mask',
                 'nfail', 'xfail')

    def __init__(self, jobname=None, backend='multiprocessing', xfail=1,
                 **config):

        self.jobname = type(self).__name__ if jobname is None else str(jobname)
        self.backend = str(backend)
        self.results = self.mask = None
        self.config = config
        self.xfail = xfail
        self.nfail = sync_manager.Value('i', 0)

    def init_memory(self, shape, masked=False, loc=None, fill=np.nan, overwrite=False):
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
        self.results = load_memmap(loc, shape, fill=fill, overwrite=overwrite)
        self.mask = None
        if masked:
            self.mask = load_memmap(loc, shape, bool, True, overwrite)

    def __call__(self, data, indices=None, **kws):
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

        return self.run(data, indices, **kws)

    def __str__(self):
        name = type(self).__name__
        if (m := self.results) is None:
            return f'{name}(0/0)'
        return f'{name}({sum(self.completed)} / {len(m)})'

    # ------------------------------------------------------------------------ #
    @property
    def completed(self):
        # boolean array flags True if frame has any measurement(s)
        return ~np.isnan(self.results).all(
            tuple({*range(self.results.ndim)} - {0})
        )

    def setup(self, njobs, progress_bar, **config):

        self.logger.opt(lazy=True).debug(
            'Compute setup: {}', lambda: pp.pformat(locals(), ignore='self')
        )

        # get njobs
        if njobs in (-1, None):
            njobs = mp.cpu_count()

        if len(self.results) == 1:
            self.logger.info('Only one job in work queue, setting `njobs=1`.')
            njobs = 1

        # setup compute context
        if njobs == 1:
            return self.compute, ctx.nullcontext(list), ()

        # locks for managing output contention
        mem_lock = sync_manager.Lock()
        prg_lock = mp.RLock()

        # set lock for progress bar stream
        tqdm.set_lock(prg_lock)

        # NOTE: object serialization is about x100-150 times faster with
        # "multiprocessing" backend. ~0.1s vs 10s for "loky".
        worker = delayed(self.compute)
        executor = Parallel(njobs, self.backend, **config)
        context = ContextStack(
            initialized(executor, set_locks, (mem_lock, prg_lock))
        )

        # Adapt logging for progressbar
        if progress_bar:
            # These catch the print statements
            context.add(TqdmLogAdapter())

        return worker, context, (mem_lock, prg_lock)

    def get_workload(self, data, indices, progress_bar=None):
        # workload iterable with progressbar if required

        # get indices
        done = self.completed
        if indices is None:
            indices, = np.where(~done)

        indices = list(indices)
        self.logger.debug('indices = {}', indices)

        # resolve xfail
        n = len(self.results)
        if isinstance(self.xfail, str):
            self.xfail = int(round(Percentage(self.xfail).of(n)))

        if isinstance(self.xfail, float):
            self.xfail = int(round(n * self.xfail))

        # check indices
        if len(indices) == 0:
            self.logger.info('All data have been processed. To force a rerun, '
                             'you may reset the memory\n'
                             ' >>> exec.init_memory(..., overwrite=True)')

            return ()

        # progress bar only if more than one task
        if progress_bar is None:
            progress_bar = (len(indices) > 1)

        # resolve data / indices
        self.logger.debug('Creating workload for {} items.', len(data))

        if isinstance(data, (np.ndarray, list)):
            workload = ((data[i], i) for i in indices)

        elif isinstance(data, abc.Iterable):
            workload = zip(data, indices)

        else:
            raise TypeError(f'Cannot create workload from data of type {type(data)}.')

        # workload iter
        return tqdm(workload, self.jobname,
                    initial=done.sum(), total=len(done),
                    disable=not progress_bar, **CONFIG.progress)

    # @api.synonyms({'n_jobs': 'njobs'})
    def run(self, data=None, indices=None, njobs=-1, progress_bar=None,
            args=(), **kws):
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

        # main compute
        self.logger.debug('indices = {}', indices)
        self.main(data, indices, njobs, progress_bar, *args, **kws)
        return self.finalize(*args, **kws)

    def main(self, data, indices, njobs, progress_bar, *extra_args, **kws):

        # setup compute context
        worker, context, locks = self.setup(njobs, progress_bar, **self.config)
        self.logger.debug('Main compute starting with indices = {}', indices)

        # Adapt logging sinks for tqdm interplay
        logger.remove()
        logger.add(TqdmStreamAdapter(), colorize=True, enqueue=True)

        # execute
        with context as compute:
            # do work
            compute(worker(*args, *extra_args, **kws) for args in
                    self.get_workload(data, indices, progress_bar))

        # self.logger.debug('With {} backend, pickle serialization took: {:.3f}s.',
        #              backend, time.time() - t_start)
        self.logger.debug('Task {} complete. Returning results.', self.jobname)
        return self.results

    def compute(self, data, index, **kws):

        # first check if we are good to continue
        if self.nfail.value >= self.xfail:
            # doing this here (instead of inside the except clause) avoids
            # duplication by chained exception traceback when logging
            raise AbortCompute(f'Reach exception threshold of {self.xfail}.')

        # compute
        try:
            result = self._compute(data, **kws)
        except Exception as err:
            #
            self.logger.exception('Compute failed for index {}:\n{}', index, err)

            # check if we should exit
            with memory_lock:
                nfail = self.nfail.value + 1
                self.nfail.value = nfail

                # check if we are beyond exception threshold
                if nfail >= self.xfail:
                    self.logger.critical('Exception threshold reached!')

                    raise AbortCompute(
                        f'Reach failure threshold of {self.xfail}.'
                    ) from err
                else:
                    self.logger.info('Continuing after {}/{} failures.',
                                     nfail, self.xfail)

        else:
            self.collect(index, result)

    def collect(self, index, result):
        # collect results
        self.results[index] = result

        # handle masked
        if self.mask is not None and np.ma.is_masked(result):
            self.mask[index] = result.mask

    def _compute(self, *data, **kws):
        raise NotImplementedError()

    def finalize(self, *args, **kws):
        logger.remove()
