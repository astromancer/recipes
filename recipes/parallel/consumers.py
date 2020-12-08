import multiprocessing as mp

#****************************************************************************************************
class BaseTask():
    '''A simple wrapper class for parallel task execusion'''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, func, *args):
        self.func = func
        self.args = args

    def __call__(self):
        return self.func(*self.args)

    def __str__(self):
        return '%s%s' % (self.func.__name__,  str(self.args))
        #return '%s(%s, ...)' % (self.func.__name__,  str(self.args[:2]))

    #def __repr__(self):


#****************************************************************************************************
#class NullCondition(ExitStack):
    #def notify_all(self):
        #pass

#from decor.expose import get_func_repr
#****************************************************************************************************
class Task(BaseTask, LoggingMixin):
    '''A simple wrapper class for parallel task execusion'''
    def __init__(self, func, *args):
        BaseTask.__init__(self, func, *args)

        self._is_done = False  #NullCondition()

        self.logger.debug('creating an instance of %s: %s'
                          %(self.__class__.__name__, str(self)))

    #@expose.args()
    def __call__(self):
        self.logger.debug('Excecuting: %s' %self)
        return self.func(*self.args)
        #if self._is_done:
            #with self._is_done:
                #self._is_done.notify_all()

        #return returned

    def __str__(self):
        #return get_func_repr(self.func, self.args)  #pretty repr
        return '%s%s' % (self.func.__name__,  str(self.args))
        #return '%s(%s, ...)' % (self.func.__name__,  str(self.args[:2]))

    #def notify_when_done(self, cond):
        #self._is_done = cond
        #return self._is_done


    #TODO: maybe add some control structure here for optionally returning the
    #result / more tasks
    #TODO: AS DECORATOR


#****************************************************************************************************
class TriggeringTask(Task):
    def __init__(self, func, args):
        Task.__init__(self, func, *args)
        self._triggers = []

    def __call__(self):
        return self.triggers(self.func(*self.args))

    def add_trigger(self, func, args=()):
        '''Add task that will be triggered upon return of the call - somehow'''
        #pre_args - arguments for the triggered task that we know beforehand
        self._triggers.append((func, args))

    def triggers(self, *args):
        triggered = Tasks([TriggeringTask(f, *pre_args, *args)
                                for f, pre_args in self._triggers])
        return triggered


#class Tasks(list):
    #pass


#class Designator():

def SENTINEL(): pass

#****************************************************************************************************
class ConsumerBase(mp.Process, LoggingMixin):
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    TIMEOUT = 3

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, inq, outq=None, **kws):
        #if 'target' not in kws:
            #raise ValueError('target required')

        #NOTE: requires a target function
        mp.Process.__init__(self, **kws)
        self.inq = inq
        self.outq = outq
        self.has_outq = outq is not None

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def run(self):

        self.logger.info('Running %s' % self.name)
        while self._continue():
            args = self.inq.get(self.TIMEOUT)
            if args is SENTINEL:
                # Poison pill means shutdown

                break

            try:
                self.main(args)
            except TimeoutError:
                self.logger.warning('TIMEOUT!')
                break
            except Exception as err:
                self.logger.exception('BORK!!')

            #self.logger.debug('calling task_done')
            self.inq.task_done()

        self.logger.debug('Run complete')
        return

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _continue(self):
        return True

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #NOTE: this could be a call method???
    def main(self, incoming):
        #NOTE: you can elliminate intermediate storage here
        pre = self.pre_process(incoming)
        #self.logger.debug('%s excecuting: %s%s'
                          #%(self.name, self._target.__name__, pre))
        answer = self._target(*pre)
        return self.post_process(incoming, answer)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def pre_process(self, data):
        return data

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def post_process(self, args, answer):
        pass

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def shutdown(self):
        '''shutdown procedure'''
        self.logger.info('%s received sentinel. Exiting.' % self.name)
        #self.logger.debug('SH*T: %s' %  self.outq.qsize())
        self.inq.task_done()


#class ConsumerBase2(ConsumerBase):
    ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def __init__(self, inq, outq, pipe, **kws):
        #self.conn = conn

    ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def run(self):

        #self.logger.info('Running %s' % self.name)
        #while self._continue():
            #args = self.inq.get(self.TIMEOUT)
            #if args is None:
                ## Poison pill means shutdown
                #self.logger.info('%s received sentinel. Exiting.' % self.name)
                ##self.logger.debug('SH*T: %s' %  self.outq.qsize())
                #self.inq.task_done()

                #self.exit.set()


                #break

            #try:
                #self.main(args)

            ##catch and log errors
            #except Exception as err:
                #tb = traceback.format_exc()
                #self.logger.exception(''.join(tb))

            #self.logger.debug('calling task_done')
            #self.inq.task_done()

        #self.logger.debug('Run returning')
        #return







#****************************************************************************************************
class TriggerBase(ConsumerBase):
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #@expose.args()
    def main(self, args):
        post = ConsumerBase.main(self, args)
        self.load_queue(post)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def load_queue(self, post):
        if post is None:
            #self.logger.debug('Nothing to post-process - continuing')
            return

        if not self.has_outq:
            self.logger.warning('no output queue to add returned items to') # %post
            return

        #self.logger.debug('%s has size %d' %(self.outq, self.outq.qsize()))
        self.logger.debug('Attempting to trigger %s', str(self._target))
        i = 0   #avoid error for empty trigger generators (i does not get defined)
        for i, args in enumerate(self.triggers(post)):
            #self.logger.debug('Plonking %s' %str(g))
            self.outq.put(args)

        self.logger.debug('%i items added to queue' %i)
        self.logger.debug('%s has size %d' %(self.outq, self.outq.qsize()))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def triggers(self, args):
        yield from ()


#****************************************************************************************************
class ProcessTask(TriggerBase):
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #NOTE: this could be a call method???
    def main(self, task):

        #NOTE: you can elliminate intermediate storage here
        self.logger.debug('%s excecuting: %s%s' % (self.name, task))
        pre = self.pre_process(task)
        answer = task()
        post =  self.post_process(pre, answer)

        self.load_queue(post)

#****************************************************************************************************
class ProcessFunc(TriggerBase):

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #NOTE: this could be a call method???
    def main(self, incoming):

        #NOTE: you can elliminate intermediate storage here
        func, args = incoming

        pre = self.pre_process(args)
        #self.logger.debug('%s excecuting: %s%s' % (self.name, func.__name__, pre))
        answer = func(*pre)
        post =  self.post_process(args, answer)

        self.load_queue(post)


#****************************************************************************************************
class MultiQTrigger(TriggerBase):
    #NOTE: this class will be unnecesary if you pass tasks into the queues.
    #the cost will be extra objects to pickle
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, inq, *outqs, **kws):
        mp.Process.__init__(self, **kws)

        self.inq = inq
        self.outqs = outqs
        self.allqs = [inq] + list(outqs)
        self.has_outq = len(outqs)

        self.logger.debug('creating an instance of Consumer')

    ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ##@expose.args()
    #def post_process(self, qi, post):
        #self.load_queue(qi, post)

    ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def load_queue(self, qi, post):
        #self.outq = self.outqs[qi]
        #TriggerBase.load_queue(self, post)

#class AutoTriggerConsumer(TriggerBase):
     #def post_process(self, post):
        #TriggerBase.post_process(self, post)


#****************************************************************************************************
class PersistantConsumer(mp.Process, LoggingMixin):
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, inq, outq, **kws):
        mp.Process.__init__(self, **kws)
        self.inq = inq
        self.outq = outq

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def run(self):
        self.logger.info('Running %s' % self.name)
        while True:
            args = self.inq.get()

            if args is None:
                # Poison pill means shutdown
                self.logger.info('%s: Exiting' % self.name)
                self.inq.task_done()
                break

            try:
                self.logger.debug('%s excecuting: %s%s' % (self.name, self._target, args))
                answer = self._target(args, self._args)    #NOTE: single argument syntax

                self.post_process(answer)

            #catch and log errors
            except Exception as err:
                tb = traceback.format_exc()
                self.logger.exception(''.join(tb))

            self.inq.task_done()

        return

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def post_process(self, args):
        pass



class AutoTriggerConsumer(mp.Process, LoggingMixin):
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, inq, *outqs, **kws):
        mp.Process.__init__(self, **kws)

        self.inq = inq
        self.outqs = outqs
        self.allqs = [inq] + list(outqs)
        self.has_outq = len(outqs)

        self.logger.debug('creating an instance of Consumer')

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def run(self):
        self.logger.info('Running %s' % self.name)
        while True:
            task = self.inq.get()

            if task is None:
                # Poison pill means shutdown
                self.logger.info('%s: Exiting' % self.name)
                self.inq.task_done()
                break

            try:
                #self.logger.debug('%s excecuting: %s%s' % (self.name, self._target, args))
                new_tasks = task()
                self.logger.debug('post_processing %s of %s' %(new_tasks, task.func))
                self.post_process(new_tasks)

            #catch and log errors
            except Exception as err:
                tb = traceback.format_exc()
                self.logger.exception(''.join(tb))

            self.inq.task_done()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def post_process(self, tasks):
        if tasks is None:
            self.logger.debug('No tasks triggered')
            return

        #OR check if returned tuple contains a Task??
        #elif isinstance(tasks, Tasks):
        self.load_queue(tasks)

        #else:
            #raise ValueError('I like tasks')

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def load_queue(self, tasks):
        if not self.has_outq:
            self.logger.warning('no output queue to add returned %s to' %args)
            return

        self.logger.debug('Triggered %d tasks' % len(tasks))
        q = self.outq
        for i, task in enumerate(tasks):
            q.put(task)

        self.logger.debug('%s has size %d' %(q, q.qsize()))
        #NOTE: since task are homogeneous, we can estimate size of queue in memory



#****************************************************************************************************

#NOTE: this class allows Tasks to trigger other tasks if they return a 2-tuple
#containing a integer, i followed by a list of Task objects.
#The horrible nested if bomb in the run method handles the logic of whether / where
#to add tasks.  i indicates which queue outgoing tasks are destined for.

#Not sure if this is much better than explicitly passing queues to functions...
#It does allow for a Task to re-insert themselves into the input queue, which is
#useful in some edge cases
#also helps keeps the control flow structures separate which is nice
class AutoTriggerConsumer2(mp.Process, LoggingMixin):      #TODO: subclass Consumer above (when mature)
    '''
    Consumer monitors a queue for tasks, adding results/additional tasks
    to an output queue.  Shutdown only on sentinel retrieval.
    '''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, inq, *outqs, **kws):
        mp.Process.__init__(self, **kws)

        self.inq = inq
        self.outqs = outqs
        self.allqs = [inq] + list(outqs)
        self.has_outq = len(outqs)

        self.logger.debug('creating an instance of Consumer')

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def loads(self, qi, data):
        #qi, triggered_tasks = returned

        if qi > -1 and not self.has_outq:
            self.logger.warning('no output queue to add returned %s '
                                'to' %returned)
        else:
            self.logger.debug('Triggered %d tasks' % len(data))
            q = self.allqs[qi+1]
            for i, datum in enumerate(data):
                q.put(datum)

            self.logger.debug('%s has size %d' %(q, q.qsize()))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def add_trigger(self, func, args=()):
        ##'''Add task that will be triggered upon return of the call - somehow'''
        ###pre_args - arguments for the triggered task that we know beforehand
        #self._triggers.append((func, args))

    ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def get_triggered_tasks(self, *args):
        #return [Task(*pre_args, *args) for f, pre_args in self._triggers]

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def run(self):
        while True:
            task = self.inq.get()
            if task is None:
                # Poison pill means shutdown
                self.inq.task_done()
                self.logger.info('%s: Exiting' % self.name)
                break

            self.logger.debug('Trying %s: %s' % (self.name, task))

            #execute the task
            try:
                returned = task()


                #self.get_triggered_tasks(*returned)

                #TODO: think of a better way of doing this,
                #maybe handle inside task.__call__ ??
                if returned is None:
                    #No tasks triggered
                    self.logger.debug('No tasks triggered')
                    pass

                #OR check if returned tuple contains a Task??
                elif len(returned)==2:
                    #loads(
                    pass
                        #NOTE: since task are homogeneous, we can estimate size of queue in memory
                else:
                   self.logger.warning('no output queue to add returned %s to' %returned)
                   #OR raise??

            #catch and log errors
            except Exception as err:
                tb = traceback.format_exc()
                self.logger.exception(''.join(tb))

            self.inq.task_done()

        return