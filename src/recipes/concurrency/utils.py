

# std
import time
import tempfile
import itertools as itt
import multiprocessing as mp

# third-party
import psutil
import numpy as np
import more_itertools as mit
from loguru import logger

# relative
from .. import pprint
from ..io import load_memmap
from ..string import Percentage
from ..logging import LoggingMixin


# class Monitor

def monCPU(filename, interval, alive, maxsize=1e6):
    i = 0
    with open(str(filename), 'w') as fp:
        while alive.is_set():
            if i < maxsize:
                occupancy = psutil.cpu_percent(interval=interval, percpu=True)
                data = [time.time()] + occupancy
                line = ', '.join(map(str, data)) + '\n'

                fp.write(line)
                i += 1


def monMEM(filename, interval, alive, maxsize=1e5):
    i = 0
    Gb = 2 ** 30
    with open(str(filename), 'w') as fp:
        while alive.is_set():
            if i < maxsize:
                t0 = time.time()
                svmem = svmem = psutil.virtual_memory()
                data = [time.time(), svmem.used / Gb, svmem.free / Gb]
                line = ', '.join(map(str, data)) + '\n'

                fp.write(line)
                i += 1

                time.sleep(interval - (t0 - time.time()))

#


def qmeasure(qs, filename, interval, alive, maxsize=1e5):
    """
    Function that measures the sizes of the queues over time and logs these to
    file.
    """
    i = 0
    with open(str(filename), 'w') as fp:
        while alive.is_set():
            if i >= maxsize:
                continue

            t0 = time.time()
            sizes = [q.qsize() for q in qs]
            data = [time.time()] + sizes
            line = ', '.join(map(str, data)) + '\n'

            fp.write(line)
            i += 1

            time.sleep(interval - (t0 - time.time()))


#
def queue_monitor(q, done, trigger, threshold, interval):
    """
    Basic queue monitor.  Triggers the load events once the (approximate) number
    of items in the queue falls below threshold value, then doesn't trigger again
    until the interval has passed.
    Note: interval should be larger than data load time.
    """
    # logger = logging.getLogger(
    #     'phot.lll.monitor')  # TODO: queue_monitor.__module__ + queue_monitor.__name__?
    logger.info('Starting: threshold={:d}.', threshold)

    while not done.is_set():
        qsz = q.qsize()
        if qsz < threshold:
            logger.info('Triggering next load.')
            trigger.set()
        else:
            logger.debug('Waiting: qsize~{:d}, threshold={:d}.', qsz, threshold)
            trigger.clear()

        logger.debug('Waiting for {:.2f} sec.', interval)
        time.sleep(interval)

#


def queues_monitor(qs, done, trigger, thresholds, interval):
    """
    Basic queue monitor.  Triggers the load events once the (approximate) number
    of items in the queue falls below threshold value, then doesn't trigger again
    until the interval has passed.
    Note: interval should be larger than data load time.
    """

    logger.info('Starting: threshold={:s}.', thresholds)

    while not done.is_set():
        qi = [(qn, q.qsize()) for qn, q in qs.items()]
        logger.debug('Queue sizes: {:s}.', qi)
        qn, qsz = zip(*qi)
        l = np.less(qsz, thresholds)
        if can_load := l.all():
            logger.info('Triggering next load.')
            trigger.set()
        else:
            ssize = '; '.join(map(' ~ '.join, np.array(qi)[~l]))
            logger.debug('Waiting on queues: {:s}, threshold={:s}.',
                         ssize, thresholds)
            trigger.clear()

        logger.debug('Waiting for {:1.2f} sec.', interval)
        time.sleep(interval)

#
#from decor import expose
# @expose.args()


def queue_loader_task(trigger, queue, done, func, data, batch_size, args=()):
    """staggers task loads into queue"""

    sentinel = None  # TODO: global??
    with_sentinel = itt.chain(data, [sentinel])
    batches = mit.ichunked(with_sentinel, batch_size)
    for i, chunk in enumerate(batches):
        # wait for trigger before loading the data
        logger.info('Waiting on trigger {:d}.', i)
        trigger.wait()

        logger.info('Load {:d} commencing.', i)
        logger.info('Adding {:d} data to queue.', len(chunk))
        for item in chunk:
            # stop loading upon sentinel value
            if item is not sentinel:
                #tsk = Task(func, item, *args)
                # print(tsk)
                queue.put(Task(func, item, *args))
            else:
                queue.put(item)  # SENTINAL
                done.set()  # triggers sentinels for consumers
                logger.info('All data loaded.')
                break

        if not done.is_set():
            logger.info('Load {:d} done.', i)
        trigger.clear()

# TODO: update docstring


def queue_loader(queue, trigger, done, data, batch_size=1, wrapper=None,
                 load_sentinel=True, sentinel=None):
    """
    Staggers data loads into queue
    Params
    ------
    trigger - multiprocessing.Event
    queue - multiprocessing.Queue
    done - multiprocessing.Event


    wrapper - optional function that takes a item from the input iterable and
             returns the objects to be put into the queue
    """

    if wrapper is not None:
        data = map(wrapper, data)

    batch_size = int(batch_size)
    if batch_size < 1:
        raise ValueError(f'Invalid `batch_size`: {batch_size}.')

    # load loop
    for i, batch in enumerate(mit.ichunked(data, batch_size)):
        # wait for trigger before loading the data
        logger.info('Waiting on trigger {:d}.', i)
        trigger.wait()

        logger.info('Loading batch {:d} of {} objects.', i, len(batch))
        for item in batch:
            queue.put(item)

        logger.info('Load {:d} done.', i)
        trigger.clear()

    # done loading - add sentinel value
    logger.info('All data loaded.')
    if load_sentinel:
        logger.debug('Adding sentinel {:s}.', sentinel)
        queue.put(sentinel)
    done.set()  # set done event

    logger.debug('queue_loader returning.')


# ****************************************************************************************************
class QueueLoader(mp.Process, LoggingMixin):
    """staggers task loads into queue"""

    # def __init__(self, group, target, name, args, kws, *, daemon):
    #     super().__init__(group, target, name, args, kws, daemon=daemon)

    def __init__(self, queue, trigger, done, data, batch_size=1, wrapper=None,
                 sentinel=None, timeout=60):
        """
        Staggers data loads into queue

        Params
        ------
        trigger - multiprocessing.Event
        queue - multiprocessing.Queue
        done - multiprocessing.Event


        wrapper - optional function that takes a item from the input iterable and
                returns the objects to be put into the queue
        """

        self.queue = queue
        self._trigger = trigger
        self.done = done

        if wrapper is not None:
            data = map(wrapper, data)

        # def __init__(self, group, target, name, args, kws, *, daemon):
        mp.Process.__init__(self, None, self._target, None,
                            (data, batch_size, sentinel, timeout), {},
                            daemon=False)
        # group should always be None; it exists solely for compatibility with
        # threading.Thread.

    def is_done(self):
        return self.done.is_set()

    def trigger(self):
        self._trigger.set()
    
    def _target(self, data, batch_size, sentinel, timeout):

        self.logger.debug('Running: {:s}.', self.name)

        with_sentinel = itt.chain(data, [sentinel])
        batches = mit.ichunked(with_sentinel, batch_size)
        for i, batch in enumerate(batches):
            # wait for trigger before loading the data
            self.logger.debug('Waiting on trigger {:d}.', i)
            self._trigger.wait(timeout)

            logger.debug('Loading batch {:d} of {} objects.', i, len(batch))
            for item in batch:
                self.queue.put(item)

            self.logger.debug('Batch {} loaded.', i)
            self._trigger.clear()

        # done loading - add sentinel value
        self.logger.info('All data loaded.')
        self.done.set()  # triggers sentinels for consumers

# ---------------------------------------------------------------------------- #


class AbortCompute(Exception):
    pass


class TaskExecutor(LoggingMixin):
    """
    Decorator that catches and logs exceptions instead of actively raising.

    Intended use is for data-parallel loops in which the same function will be
    called many times with different parameters. For this class to work
    properly, it requires the decorated function/method to have a call signature
    in which the first parameter is an integer count corresponding to the
    in-sequence number of the task.
    """
    SUCCESS = 1
    FAIL = -1

    def __init__(self, compute_size, counter, fail_counter, max_fail=None,
                 time=False):
        """


        Parameters
        ----------
        compute_size
        counter
        fail_counter
        max_fail:
            percentage string eg: '1%' or an integer

        """
        # TODO: timer
        # TODO: make progressbar optional

        self.compute_size = n = int(compute_size)
        self.loc = tempfile.mktemp()
        self.status = load_memmap(self.loc, n, 'i', 0)
        self.counter = counter
        self.fail_counter = fail_counter
        self.time = bool(time)
        self.timings = None
        if self.time:
            self.loct = tempfile.mktemp()
            self.timings = load_memmap(self.loct, n, 'f', 0)

        # resolve `max_fail`
        if max_fail is None:
            # default is 1% or 50, whichever is smaller
            max_fail = min(Percentage('1%')(n), 50)
        else:
            max_fail = Percentage(max_fail)(n)
        self.max_fail = max_fail

        # progress "bar"
        self.progLog = ProgressLogger(width=10, symbol='', align='<')
        self.progLog.create(n, None)

    def __call__(self, func):

        self.func = func
        self.name = pprint.method(func, show_class=True, submodule_depth=1)
        self.progLog.name = self.name

        # optional timer
        self.run = self._run_timed if self.time else self._run

        # log
        # if np.isfinite(max_fail):
        n = self.compute_size

        self.logger.info('Exception threshold is {:.2%} ({:d}/{:d}).' % (
            (self.max_fail / n), self.max_fail, n))

        return self.catch

    # @property  # making this a property avoids pickling errors for the logger
    # def logger(self):
    #     logger = logging.getLogger(self.name)
    #     return logger

    def reset(self):
        self.counter.set_value(0)
        self.fail_counter.set_value(0)

    def _run(self, *args, **kws):
        return self.func(*args, **kws)

    def _run_timed(self, *args, **kws):
        ts = time.time()
        result = self.func(*args, **kws)
        self.timings[args[0]] = time.time() - ts
        return result

    def catch(self, *args, **kws):
        """
        This is the decorated function

        Parameters
        ----------
        args
        kws

        Returns
        -------

        """
        # exceptions like moths to the flame
        abort = self.fail_counter.get_value() >= self.max_fail
        if abort:
            # doing this here (instead of inside the except clause) avoids
            # duplication by chained exception traceback when logging
            raise AbortCompute('Reach failure threshold of {self.max_fail}.')

        try:
            result = self.run(*args, **kws)
        except Exception as err:
            # logs full trace by default
            i = args[0]
            self.status[i] = self.FAIL
            nfail = self.fail_counter.inc()
            self.logger.exception(
                'Processing failed at frame {:d}. ({:d}/{:d})',
                i, nfail, self.max_fail
            )

            # check if we are beyond exception threshold
            if nfail >= self.max_fail:
                self.logger.critical('Exception threshold reached!')
                # self.logger.critical('Exception threshold reached!')
        else:
            i = args[0]
            self.status[i] = self.SUCCESS
            return result  # finally clause executes before this returns

        finally:
            # log progress
            if counter := self.counter:
                n = counter.inc()
                if self.progLog:
                    self.progLog.update(n)

    def report(self):
        # not_done, = np.where(self.status == 0)
        failures, = np.where(self.status == -1)
        n_done = self.counter.get_value()
        n_fail = self.fail_counter.get_value()

        # TODO: one multi-line message better when multiprocessing

        self.logger.info('Processed {:d}/{:d} frames. {:d} successful; {:d} failed.',
                         n_done, self.compute_size, n_done - n_fail, n_fail)
        if len(failures):
            self.logger.info('The following frames failed: {:s}.', list(failures))
        elif n_done > 0:
            self.logger.info('No failures in main compute!')

        if self.time:
            #  print timing info
            self.logger.info('Timing results for {:s}: {:.3f} ± {:.3f} s.',
                             self.name, self.timings.mean(), self.timings.std())

        return failures
