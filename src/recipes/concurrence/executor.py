
# std
import contextlib as ctx
import multiprocessing as mp

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
from ..oo.property import Alias
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


def select(indices, *data):
    if data:
        for i in indices:
            yield _select(i, *data)


def _select(index, *data):
    return tuple((array[index] for array in data))


# ---------------------------------------------------------------------------- #
class AbortCompute(Exception):
    pass


class Framework(SlotHelper, LoggingMixin):

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

    def __call__(self, *data, **kws):
        """
        Run compute by invoking the `run` method.
        """
        return self.run(*data, **kws)

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
            return self._compute, ctx.nullcontext(list), ()

        # locks for managing output contention
        mem_lock = sync_manager.Lock()
        prg_lock = mp.RLock()

        # set lock for progress bar stream
        tqdm.set_lock(prg_lock)

        # NOTE: object serialization is about x100-150 times faster with
        # "multiprocessing" backend. ~0.1s vs 10s for "loky".
        worker = delayed(self._compute)
        executor = Parallel(njobs, self.backend, **config)
        context = ContextStack(
            initialized(executor, set_locks, (mem_lock, prg_lock))
        )

        # Adapt logging for progressbar
        if progress_bar:
            # These catch the print statements
            context.add(TqdmLogAdapter())

        return worker, context, (mem_lock, prg_lock)

    def get_workload(self, *data, progress_bar=False, jobname='', **kws):
        # workload iterable with progressbar if required

        self.logger.debug('Creating workload for {} items.', len(data))

        workload = self._get_workload(*data)

        # workload iter
        return tqdm(workload,
                    **{**dict(desc=(jobname or self.jobname),
                              disable=not progress_bar),
                       **CONFIG.progress,
                       'total': len(data[0]),
                       **kws})

    def _get_workload(self, *data):
        # NOTE: should yield (data, index) since that is what the `_compute`
        # method expects.
        return zip(*data)

    # @api.synonyms({'n_jobs': 'njobs', 'job_name': 'jobname'})
    def run(self, *data, njobs=-1, progress_bar=None, jobname='',
            args=(), **kws):
        """
        Start a job. The workload will be split into
        chunks of size ``

        Parameters
        ----------
        *data : tuple
            Any number of data sequences. If given, these should be the same size
            as `indices`, since we will select from each of these with the given
            indices.
        njobs : int, optional
            Number of concurrent worker processes to launch, by default -1, which
            uses the number of cpus available on the machine.
        progress_bar : bool, optional
            Whether to show progress bar (via tqdm). The default None, will only
            show this if there is more than one task.
        jobname: str, optional
            Job name to display in the progress bar.
        args: tuple
            Argument tuple passed to the workers.
        **kws:
            Keyword parameters passed to the workers.

        Raises
        ------
        FileNotFoundError
            If memory has not been initialized prior to calling this method.
        """

        # main compute
        self.main(data, njobs, progress_bar, jobname, *args, **kws)
        return self.finalize(*args, **kws)

    def main(self, data, njobs, progress_bar, jobname, *args, **kws):

        # fetch work
        workload = self.get_workload(*data,
                                     progress_bar=progress_bar, jobname=jobname)

        # setup compute context
        worker, context, locks = self.setup(njobs, progress_bar, **self.config)
        # self.logger.debug('Compute starting with indices: {}', indices)

        # Adapt logging sinks for tqdm interplay
        logger.remove()
        logger.add(TqdmStreamAdapter(), colorize=True, enqueue=True)

        # execute
        with context as compute:
            # do work
            compute(worker(*load, *args, **kws) for load in workload)
            # load - pre distributed (in `get_workload`) (index, ...)
            # data - distributed in worker process `_compute` (arrays)

        # self.logger.debug('With {} backend, pickle serialization took: {:.3f}s.',
        #              backend, time.time() - t_start)
        self.logger.debug('Task {} complete. Returning results.', self.jobname)
        return self.results

    def _compute(self, index, *args, **kws):

        # first check if we are good to continue
        if self.nfail.value >= self.xfail:
            # doing this here (instead of inside the except clause) avoids
            # duplication by chained exception traceback when logging
            raise AbortCompute(f'Reach exception threshold of {self.xfail}.')

        # compute
        try:
            result = self.compute(*args, **kws)
        except Exception as err:
            #
            self.logger.exception('Compute failed for index {}:\n{}', index, err)

            # check if we should exit
            with memory_lock:
                nfail = self.nfail.value + 1
                self.nfail.value = nfail

                # check if we are beyond exception threshold
                if nfail >= self.xfail:
                    if nfail > 1:
                        self.logger.critical('Exception threshold reached!')
                        raise AbortCompute(
                            f'Reach failure threshold of {self.xfail}.'
                        ) from err
                    else:
                        raise err
                else:
                    self.logger.info('Continuing after {}/{} failures.',
                                     nfail, self.xfail)

        else:
            self.collect(index, result)

    def collect(self, index, result):
        # collect results
        self.results[index] = result

    def compute(self, *data, **kws):
        raise NotImplementedError

    def finalize(self, *args, **kws):
        logger.remove()
        return self.results


class Executor(Framework):
    """
    Failure tolerant parallel task executor with flexible backend, data
    persistence and progress monitoring.
    """

    # aliases
    reset = Alias('reset_memory')
    get_index = Alias('select')

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

    def __call__(self, indices=None, *data, **kws):
        """
        Run compute by invoking the `run` method.

        Parameters
        ----------
        data: Sequence
            Data to compute, typically a np.ndarray.
        indices: Sequence[int]
            Indices of data array to compute, by default

        Returns
        -------
        results
        """

        if self.results is None:
            raise FileNotFoundError('Initialize memory first by calling the '
                                    '`init_memory` method.')

        return self.run(*data, indices=indices, **kws)

    def __str__(self):
        return f'{type(self).__name__}({self.completeness})'

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
            return '0/0'

        return f'{self.completed.sum()}/{len(self.results)}'

    # ------------------------------------------------------------------------ #
    def get_workload(self, indices=None, *distributed, progress_bar=None, jobname='', **kws):
        # workload iterable with progressbar if required

        # get indices
        done = self.completed
        if done.all():
            self.logger.info('All data have been processed. To force a rerun, '
                             'you may reset the memory\n'
                             ' >>> exec.reset_memory()')

            return ()

        # Resolve indices - need these to write results
        if indices is None:
            indices, = np.where(~done)

        indices = list(indices)
        self.logger.debug('indices = {}', indices)

        # progress bar only if more than one task
        if progress_bar is None:
            progress_bar = (len(indices) > 1)

        # get workload
        # NOTE: array data should not be "distributed", since there is a cpu and
        # memory overhead associated with pickling arrays vs pickling memmory
        # maps, which will happen in the main process joblib automatically
        # convert arrays to memmaps, so prefered recipe is to select data from
        # the memory map within the worker process.
        return super().get_workload(indices, *distributed,
                                    jobname=jobname, progress_bar=progress_bar,
                                    initial=done.sum(), total=len(done), **kws)

    # @api.synonyms({'n_jobs': 'njobs', 'job_name': 'jobname'})
    def run(self, *data, indices=None, njobs=-1, progress_bar=None, jobname='',
            args=(), **kws):
        """
        Start a job. The workload will be split into
        chunks of size ``

        Parameters
        ----------
        *data : tuple
            Any number of data sequences. If given, these should be the same size
            as `indices`, since we will select from each of these with the given
            indices.
        indices : Iterable, optional
            Indices of dara frames to compute. If None, the default, the
            `results` array is inspected to get indices of all unprocessed data.
        njobs : int, optional
            Number of concurrent worker processes to launch, by default -1, which
            uses the number of cpus available on the machine.
        progress_bar : bool, optional
            Whether to show progress bar (via tqdm). The default None, will only
            show this if there is more than one task.
        jobname: str, optional
            Job name to display in the progress bar.
        args: tuple
            Argument tuple passed to the workers.
        **kws:
            Keyword parameters passed to the workers.

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
        args = (*data, *args)
        super().main((indices, ), njobs, progress_bar, jobname, *args, **kws)
        return self.finalize(*args, **kws)

    def select(self, index, *data):
        return _select(index, *data)

    def _compute(self, index, *distributed, args=(), **kws):
        # select indexed arrays
        _args = self.select(index, *distributed)
        return super()._compute(index, *_args, *args, **kws)


class BatchedExecutor(Executor):

    def setup(self, njobs, progress_bar, **config):
        _, context, locks = super().setup(njobs, progress_bar, **config)
        return delayed(self.loop), context, locks

    def get_workload(self, indices=None, *distributed, progress_bar=None, jobname=''):

        #
        workload = super().get_workload(indices, *distributed,
                                        progress_bar=progress_bar, jobname=jobname)

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
