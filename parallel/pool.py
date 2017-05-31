
import multiprocessing as mp

from recipes.logging import LoggingMixin

# ===============================================================================
class ConservativePool(mp.pool.Pool):
    """
    Subclass of Pool which avoid making a potentially huge list when mapping over a function
    and is therefor more memory efficient
    """
    def _map_async(self, func, iterable, mapper, chunksize, callback=None,
                   error_callback=None):
        """
        Helper function to implement map, starmap and their async counterparts.
        """
        if self._state != 0:
            raise ValueError("Pool not running")
            #


        if chunksize is None:
            raise ValueError('Need chunksize')

        task_batches = self.__class__._get_tasks(func, iterable, chunksize)
        result = mp.pool.MapResult(self._cache, chunksize, N, callback,
                                   error_callback=error_callback)
        self._taskqueue.put((((result._job, i, mapper, (x,), {})
                              for i, x in enumerate(task_batches)), None))
        return result


#****************************************************************************************************
class ProcessPool(LoggingMixin):
    '''A trimmed down version of mp.pool.Pool'''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, inq, outq=None, processes=None, **kws):

        self.inq = inq
        self.outq = outq
        self.maintain = kws.get('maintain')
        self._kws = kws

        #self._state = RUN

        if processes is None:
            processes = os.cpu_count() or 1

        self._processes = processes
        self._pool = []
        self._repopulate_pool()

        self._worker_handler = threading.Thread(target=ProcessPool._handle_workers,
                                                args=(self,))
        self._worker_handler.daemon = True
        self._worker_handler._state = RUN
        self._worker_handler.start()

        #self._worker_monitor = threading.Thread(target=ProcessPool._monitor_workers,
                                                #args=(self,))
        #self._worker_monitor._state = RUN
        #self._worker_monitor.start()


    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _maintain_pool(self):
        """Clean up any exited workers and start replacements for them.
        """
        if self._join_exited_workers():
            if  self.maintain.is_set():
                self._repopulate_pool()
                time.sleep(0.1)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _join_exited_workers(self):
        """Cleanup after any worker processes which have exited due to reaching
        their specified lifetime.  Returns True if any workers were cleaned up.
        """
        cleaned = False
        for i in reversed(range(len(self._pool))):
            worker = self._pool[i]
            if worker.exitcode is not None:
                # worker exited
                self.logger.info('cleaning up worker %d' % i)
                worker.join()
                self.logger.info('joined %s' %worker)
                cleaned = True
                del self._pool[i]

        #alive = sum([p.is_alive() for p in self._pool])
        #worked = [p._completed.value() for p in self._pool]
        #names = [p.name for p in self._pool]
        #self.logger.info('Done cleaning. workers: %i; active: %i;\n%s\n%s'
                         #'' % (len(self._pool), alive, str(names), str(worked)))
        return cleaned

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _repopulate_pool(self):
        """Bring the number of pool processes up to the specified number,
        for use after reaping workers which have exited.
        """
        for i in range(self._processes - len(self._pool)):
            w = self.Process(self.inq, self.outq, **self._kws)
            self._pool.append(w)
            #w.name = w.name.replace('Process', 'PoolWorker')
            w.daemon = False
            w.start()
            self.logger.info('Added worker')

        #alive = sum([p.is_alive() for p in self._pool])
        self.logger.info('Repopulated: workers: %i;' % (len(self._pool), ))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _handle_workers(pool):
        thread = threading.current_thread()

        # Keep maintaining workers maintain condition is set
        i = 0
        while thread._state == RUN:
            i += 1
            if not (i % 5):
                worked = [p._completed.value() for p in pool._pool]
                pool.logger.debug('Tasks completed: %s' %str(worked))
            pool._maintain_pool()
            time.sleep(0.1)

        pool.logger.debug('worker handler exiting')

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #@staticmethod
    #def _monitor_workers(pool):
        #thread = threading.current_thread()

        #while pool.maintain.is_set():#thread._state == RUN:
            ##alive = sum([p.is_alive() for p in pool._pool])
            #pool.logger.info('# workers: %i' % (len(pool._pool),))
            #time.sleep(0.1)


            ##alive = sum([p.is_alive() for p in pool._pool])
            #worked = [p._completed.value() for p in pool._pool]
            #names = [p.name for p in pool._pool]
            #pool.logger.info('workers: %i;\n%s\n%s'
                    #'' % (len(pool._pool), str(names), str(worked)))

        #pool.logger.debug('_monitor_workers exiting')

    ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def kill_switch(self, sentinel=None):
        #self.logger.info('%s adding %i sentinels' %(self, len(self._pool)))
        #for w in self._pool:
            #self.inq.put(sentinel)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def close(self):
        #self.logger.info('closing pool')

        #if self._state == RUN:
            #self._state = CLOSE
            #self._worker_handler._state = CLOSE


        #self.logger.info('Adding %i sentinels' %len(self._pool))
        #for w in self._pool:
            #self.inq.put(None)
            #self.logger.debug('sentinel added')


    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def join(self):

        self.logger.debug('joining pool: %s' %self)
        self.logger.info('# workers: %i; ' % (len(self._pool), ))

        #Add a poison pill for each process in the pool
        for _ in range(len(self._pool)):
            self.inq.put(SENTINEL)

        #NOTE:
        #We expect that the pool will join all the exited processes.  However,
        #sometimes we are stuck with processes that never read anything from the
        #queue at all during their lifetime (only the dark lord knows why this
        #happens). Here we circumvent the deadlock with a timeout and termination #HACK
        #FIXME: Figure out why these processes sometimes get stuck like this to
        #avoid all this cruft!
        TIMEOUT = 5
        kill_switch = False
        start = time.time()
        while time.time() - start <= TIMEOUT:
            if any(p.is_alive() for p in self._pool):
                time.sleep(.1)  # Just to avoid hogging the CPU
            else:
                self.logger.info('All processes successfully joined')
                break
        else:
            self.logger.warning('TIMEOUT!')
            kill_switch = True

        #stop worker handler that has been trying to join the exited processes
        self._worker_handler._state = CLOSE
        self._worker_handler.join()
        self.logger.debug('_worker_handler joined')

        # We only enter this if we didn't 'break' above.
        if kill_switch:
            self.logger.warning(
                'These processes did not join before %.1f timeout: (%s). '
                'Killing them now.' % (TIMEOUT, ', '.join(map(str,self._pool)))
                )
            for p in self._pool:
                p.terminate()
                p.join()

            self.logger.info('Killing spree complete')

        #the queue may not be empty because of passive (fucked up) workers
        #(or some other reason!!??)
        while True:
            leftover = []
            try:
                leftover.append(self.inq.get_nowait())
                self.inq.task_done()
            except Empty:
                logging.debug('Queue is empty!')
                break
        if len(leftover):
            self.logger.warning('The following shit was left in the queue: %s'
                           % str(leftover))

        # All the processes in the pool are now stopped
        self.inq.join()
        self.logger.info('Queue joined: %s' %self)