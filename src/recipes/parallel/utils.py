

# std
import time
import logging
import itertools as itt
import multiprocessing as mp

# third-party
import psutil
import numpy as np

# local
from recipes.iter import chunker
from recipes.logging import LoggingMixin
# import ctypes
# import traceback
# from contextlib import ExitStack




#====================================================================================================
def monCPU(filename, interval, alive, maxsize=1e6):
    i = 0
    fp = open(str(filename), 'w')
    while alive.is_set():
        if i < maxsize:
            occupancy = psutil.cpu_percent(interval=interval, percpu=True)
            data = [time.time()] + occupancy
            line = ', '.join(map(str, data)) + '\n'

            fp.write(line)
            i += 1
    else:
        fp.close()


def monMEM(filename, interval, alive, maxsize=1e5):
    i = 0
    fp = open(str(filename), 'w')
    Gb = 2 ** 30
    while alive.is_set():
        if i < maxsize:
            t0 = time.time()
            svmem = svmem = psutil.virtual_memory()
            data = [time.time(), svmem.used / Gb, svmem.free / Gb]
            line = ', '.join(map(str, data)) + '\n'

            fp.write(line)
            i += 1

            time.sleep(interval - (t0 - time.time()))
    else:
        fp.close()

#====================================================================================================
def qmeasure(qs, filename, interval, alive, maxsize=1e5):
    '''
    Function that measures the sizes of the queues over time and logs these to
    file.
    '''
    i = 0
    fp = open(str(filename), 'w')
    while alive.is_set():
        if i < maxsize:
            t0 = time.time()
            sizes = [q.qsize() for q in qs]
            data = [time.time()] + sizes
            line = ', '.join(map(str, data)) + '\n'

            fp.write(line)
            i += 1

            time.sleep(interval - (t0 - time.time()))
    else:
        fp.close()


#====================================================================================================
def queue_monitor(q, done, trigger, threshold, interval):
    '''
    Basic queue monitor.  Triggers the load events once the (approximate) number
    of items in the queue falls below threshold value, then doesn't trigger again
    until the interval has passed.
    Note: interval should be larger than data load time.
    '''
    logger = logging.getLogger('phot.lll.monitor')  #TODO: queue_monitor.__module__ + queue_monitor.__name__?
    logger.info('Starting: threshold=%i' %threshold)

    while not done.is_set():
        qsz = q.qsize()
        if qsz < threshold:
            logger.info('Triggering next load')
            trigger.set()
        else:
            logger.debug('Waiting: qsize~%i, threshold=%i' % (qsz, threshold))
            trigger.clear()

        logger.debug('Waiting for %1.2f sec' % interval)
        time.sleep(interval)

#====================================================================================================
def queues_monitor(qs, done, trigger, thresholds, interval):
    '''
    Basic queue monitor.  Triggers the load events once the (approximate) number
    of items in the queue falls below threshold value, then doesn't trigger again
    until the interval has passed.
    Note: interval should be larger than data load time.
    '''
    logger = logging.getLogger('phot.lll.monitor')  #TODO: queue_monitor.__module__ + queue_monitor.__name__?
    logger.info('Starting: threshold=%s' %thresholds)

    while not done.is_set():
        qi = [(qn, q.qsize()) for qn, q in qs.items()]
        logger.debug('Queue sizes: %s' %str(qi))
        qn, qsz = zip(*qi)
        l = np.less(qsz, thresholds)
        can_load = l.all()
        if can_load:
            logger.info('Triggering next load')
            trigger.set()
        else:
            ssize = '; '.join(map(' ~ '.join, np.array(qi)[~l]))
            logger.debug('Waiting on queues: %s, threshold=%s' % (ssize, thresholds))
            trigger.clear()

        logger.debug('Waiting for %1.2f sec' % interval)
        time.sleep(interval)

#====================================================================================================
#from decor import expose
#@expose.args()
def queue_loader_task(trigger, queue, done, func, data, chunksize, args=()):
    '''staggers task loads into queue'''

    logger = logging.getLogger('phot.lll.loader')
    #logger.debug('Running:' )

    sentinel = None         #TODO: global??
    with_sentinel = itt.chain(data, [sentinel])
    chunks = grouper(with_sentinel, chunksize)
    for i, chunk in enumerate(chunks):
        #wait for trigger before loading the data
        logger.info('Waiting on trigger %i' %i)
        trigger.wait()

        logger.info('Load %i commencing' %i)
        logger.info('Adding %i data to queue' %len(chunk))
        for datum in chunk:
            #stop loading upon sentinel value
            if datum is not sentinel:
                #tsk = Task(func, datum, *args)
                #print(tsk)
                queue.put(Task(func, datum, *args))
            else:
                queue.put(datum)            #SENTINAL
                done.set()                    #triggers sentinels for consumers
                logger.info('All data loaded')
                break

        if not done.is_set():
            logger.info('Load %i done' %i)
        trigger.clear()

#TODO: update docstring
def queue_loader(trigger, queue, done, data, chunksize, loader=None,
                 load_sentinel=True, sentinel=None):
    '''
    Staggers data loads into queue
    Params
    ------
    trigger - multiprocessing.Event
    queue - multiprocessing.Queue
    done - multiprocessing.Event


    loader - optional function that takes a datum from the input iterable and
             returns the objects to be put into the queue
    '''

    logger = logging.getLogger('phot.lll.loader')
    #logger.debug('Running:' )

    if loader is not None:
        data = map(loader, data)

    chunksize = int(chunksize)
    if chunksize == 1:
        chunks = [data]             #maybe not so efficient
    elif chunksize > 1:
        chunks = chunker(data, chunksize)
    else:
        raise ValueError('invalid chunksize')

    #load loop
    for i, chunk in enumerate(chunks):
        #wait for trigger before loading the data
        logger.info('Waiting on trigger %i' %i)
        trigger.wait()

        logger.info('Load %i commencing' %i)
        logger.info('Adding %i data to queue' %len(chunk))
        for datum in chunk:
            queue.put(datum)

        logger.info('Load %i done' %i)
        trigger.clear()

    else:
        #done loading - add sentinel value
        logger.info('All data loaded')
        if load_sentinel:
            logger.debug('adding sentinel %s' % sentinel)
            queue.put(sentinel)
        done.set()                    #set done event

    logger.debug('queue_loader returning')



#****************************************************************************************************
class Qloader(mp.Process, LoggingMixin):
    '''staggers task loads into queue'''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    sentinel = None
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, queue,  **kws):
        #mp.Process.__init__(self, **kws)
        self.q = queue
        self._is_done = False

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def is_done(self):
        if self._is_done:
            return self._is_done.is_set()
        return False

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def done(self):
        if self._is_done:
            self._is_done.set()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def notify_when_done(self):
        self._is_done = mp.Event()
        return self._is_done

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def run(self, trigger, data, chunksize):

        logger.debug('Running: %s' %self.name )

        with_sentinel = itt.chain(data, [self.sentinel])
        chunks = grouper(with_sentinel, chunksize)
        for i, chunk in enumerate(chunks):
            #wait for trigger before loading the data
            self.logger.info('Waiting on trigger %i' %i)
            trigger.wait()

            self.logger.info('Load %i commencing' %i)
            self.logger.info('Adding %i data to queue' %len(list(filter(None, chunk))))
            for datum in chunk:
                #tsk = Task(func, datum, *args)
                self.q.put(datum)

                #stop loading upon sentinel value
                if datum is self.sentinel:
                    self.logger.info('All data loaded. Adding sentinel')
                    self.done()   #triggers sentinels for consumers
                    break

            if not self.is_done():
                self.logger.info('Load %i done' %i)
            trigger.clear()





#import time

#def func(arr):
    #for i in range(50):
        #time.sleep(0.01)
        ##with lock:
        #arr[:] += i

if __name__ == '__main__':
    counter = SyncedArray(shape=(4,))
    #procs = [mp.Process(target=func, args=(counter,)) for i in range(10)]

    #for p in procs:
        #p.start()
    #for p in procs:
        #p.join()

    #print(counter)



