
# std
import contextlib as ctx
import multiprocessing as mp
from collections import abc

# third-party
import numpy as np
import more_itertools as mit
from tqdm import tqdm
from loguru import logger
from joblib import Parallel, delayed

# local
import motley

# relative
from .. import pprint as pp
from ..io import load_memmap
from ..string import pluralize
from ..config import ConfigNode
from ..oo.slots import SlotHelper
from ..oo.represent import Represent
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

def resolve_njobs(njobs):
    # get njobs
    if njobs in (-1, None):
        return mp.cpu_count()

    return int(njobs)


# ---------------------------------------------------------------------------- #

class AbortCompute(Exception):
    pass


class Executor(SlotHelper, LoggingMixin):

    __slots__ = ('jobname', 'backend', 'config', 'results', 'nfail', 'xfail')

    __repr__ = Represent((..., 'completeness'),
                         ignore=('results', ),
                         remap={'nfail': 'nfail.value'},
                         newline='\n')

    def __init__(self, jobname=None, backend='multiprocessing', xfail=1,
                 **config):

        super().__init__(
            results=None,
            config=config,
            backend=str(backend),
            xfail=xfail,
            nfail=sync_manager.Value('i', 0),
            jobname=(type(self).__name__ if jobname is None else str(jobname))
        )

    def init_memory(self, shape, loc=None, fill=np.nan, overwrite=False, **kws):
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
        self.results = load_memmap(loc, shape, fill=fill, overwrite=overwrite, **kws)

    def reset_memory(self):
        self.results[:] = np.nan

    def __call__(self, data, indices=None, **kws):
        """
        Run compute by invoking the `run` method.

        Parameters
        ----------
        data
        indices

        Returns
        -------
        results
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

    @property
    def completeness(self):
        if self.results is None:
            return '0'

        return f'{self.completed.sum()}/{len(self.results)}'

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

    def get_workload(self, data, indices=None, progress_bar=None, jobname='', **kws):
        # workload iterable with progressbar if required

        # get indices
        done = self.completed
        if indices is None:
            indices, = np.where(~done)

        indices = list(indices)
        # self.logger.debug('indices = {}', indices)

        # check indices
        if len(indices) == 0:
            self.logger.info('All data have been processed. To force a rerun, '
                             'you may reset the memory\n'
                             ' >>> exec.reset_memory()')

            return ()

        # progress bar only if more than one task
        if progress_bar is None:
            progress_bar = (len(indices) > 1)

        #
        self.logger.debug('Creating workload for {} items.', len(indices))
        workload = self._get_workload(data, indices, **kws)

        # workload iter
        return tqdm(workload, jobname or self.jobname,
                    initial=done.sum(), total=len(done),
                    disable=not progress_bar, **CONFIG.progress)

    def _get_workload(self, data, indices, **kws):
        # resolve data / indices
        if isinstance(data, (np.ndarray, list)):
            return ((data[i], i) for i in indices)

        elif isinstance(data, abc.Iterable):
            return zip(data, indices)

        raise TypeError(f'Cannot create workload from data of type {type(data)}.')

    # @api.synonyms({'n_jobs': 'njobs', 'job_name': 'jobname'})
    def run(self, data=None, indices=None, njobs=-1, progress_bar=None, jobname='',
            args=(), **kws):
        """
        Start a job. The workload will be split into
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

        # main compute
        self.main(data, indices, njobs, progress_bar, jobname,  *args, **kws)
        return self.finalize(*args, **kws)

    def main(self, data, indices, njobs, progress_bar, jobname, *extra_args, **kws):

        # fetch work
        workload = self.get_workload(data, indices, progress_bar, jobname=jobname)

        # setup compute context
        worker, context, locks = self.setup(njobs, progress_bar, **self.config)
        # self.logger.debug('Compute starting with indices: {}', indices)

        # Adapt logging sinks for tqdm interplay
        logger.remove()
        logger.add(TqdmStreamAdapter(), colorize=True, enqueue=True)

        # execute
        with context as compute:
            # do work
            compute(worker(*args, *extra_args, **kws) for args in workload)

        # self.logger.debug('With {} backend, pickle serialization took: {:.3f}s.',
        #              backend, time.time() - t_start)
        self.logger.debug('Task {} complete. Returning results.', self.jobname)
        return self.results

    def _compute(self, data, index, **kws):

        # first check if we are good to continue
        if self.nfail.value >= self.xfail:
            # doing this here (instead of inside the except clause) avoids
            # duplication by chained exception traceback when logging
            raise AbortCompute(f'Reach exception threshold of {self.xfail}.')

        # compute
        try:
            result = self.compute(data, index, **kws)
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

    def compute(self, *data, **kws):
        raise NotImplementedError()

    def finalize(self, *args, **kws):
        logger.remove()
        return self.results


class BatchedExecutor(Executor):

    def setup(self, njobs, progress_bar, **config):
        _, context, locks = super().setup(njobs, progress_bar, **config)
        return delayed(self.loop), context, locks

    def get_workload(self, data, indices, njobs=-1, batch_size=None,
                     progress_bar=None, jobname=''):

        #
        workload = super().get_workload(data, indices, progress_bar, jobname)

        if not workload:
            return ()

        n = len(self.results)
        njobs = resolve_njobs(njobs)

        if batch_size is None:
            batch_size = (n // njobs) + (n % njobs)

        # divide work
        batches = mit.chunked(workload, batch_size)
        n_batches = round(n / batch_size)

        #
        self.logger.opt(lazy=True).info(
            'Work split into {0[0]} batches of {0[1]} elements each, using {0[2]} {0[3]}.',
            lambda: (n_batches, batch_size, njobs,
                     pluralize('worker', plural='concurrent workers', n=njobs))
        )

        return batches

    def loop(self, itr, *args, **kws):
        for data in itr:
            self._compute(*data, *args, **kws)
