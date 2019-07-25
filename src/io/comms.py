import threading
import queue
from subprocess import Popen, PIPE
from collections import defaultdict


#from IPython import embed


class ProcessCommunicator(object):
    #TODO: update docstrings
    #====================================================================================================
    def __init__(self):
        '''This class collects the output from a subprocess (output and error) without blocking
        (unlike subprocess.communicate which always blocks).  Output is collected in the qo and 
        '''
        
        self.p = Popen( ['/bin/bash', '-i'], 
                        shell=True, #bufsize=1, universal_newlines=True,
                        stdin=PIPE, stdout=PIPE, stderr=PIPE )
        
        self.running = True
        self.sentinal = '!'*10                  #flag which tells the communicator when the sent command is done
        self.error_sentinal = '+'*10            #This will intentially produce an error when sent to the subprocess - we use this as a sentinal to check whether the real process produced an error
        self.logopen = False
        
        #Input queue
        self.qi = queue.Queue()
        
        #Output queue
        self.qo = queue.Queue()
        self.to = threading.Thread( name='output collection',
                                    target=self.enqueue,
                                    args=(self.qo, self.p.stdout) )
        self.to.daemon = True  # thread dies with the program
        self.to.start()
        
        #Error queue
        self.qe = queue.Queue()
        self.te = threading.Thread(name='error collection',
                                   target=self.enqueue,
                                   args=(self.qe, self.p.stderr))
        self.te.daemon = True  # thread dies with the program
        self.te.start()
        
        #print( self.to.name, 'isAlive', self.to.isAlive() )
        #print( self.te.name, 'isAlive', self.te.isAlive() )
        #print( 'self.qi.qsize()', self.qi.qsize() )
        #print( 'self.qo.qsize()', self.qo.qsize() )
        #print( 'self.qe.qsize()', self.qe.qsize() )
        
    #====================================================================================================
    def enqueue(self, q, pipe):
        '''Collect output / error from the pipe and put it in the output / error queue.'''
        if not pipe or pipe.closed:
            return
        
        for line in iter(pipe.readline, b''):                   #This catches the readline wait.
            line = line.decode().strip('\n')
            q.put( line )
    
    #====================================================================================================
    def is_sentinal(self, line):
        return (self.sentinal in line) or (self.error_sentinal in line)
    
    #====================================================================================================       
    def get_streams(self, active_print=0, log=None):
        #TODO: USE LOGGING library??
        #TODO: subclass queue to improve design
        line = '' 
        streams = defaultdict(list)
        Qs = [self.qo, self.qe]
        
        if log: 
            lognames = [log+'.out', log+'.err']
        logs = dict( zip(Qs, [False]*len(Qs) ) )
        
        while len(Qs):               #continuously try to grab output from queue until sentinal is returned --> child process has completed
            for q in Qs:
                iserror = q is self.qe
                try:
                    line = q.get_nowait()  # or q.get(timeout=.1)       #will raise Empty if queue is empty
                except Empty:
                    pass
                else:
                    #figure out which queue we are dealing with and pop it from the list Qs
                    if self.is_sentinal(line):
                        ipop = int(iserror) if len(Qs)>1 else 0
                        Qs.pop( ipop )
                        if logs[q]: logs[q].close() #print( 'Closing log', self.fplog.name )
                        break
                
                    streams[q] += [line]
                    
                    if active_print:                #print items from the output queue  whenever they become available
                        self.active_print( line, iserror )
                
                    if not log is None:             #We do this here because we don't know apriori whether creating an error/warning log will be necesarry.  Here it is created only when the first line from the error queue is returned 
                        if logs[q]:
                            logs[q].write( line+'\n' )          #self.log(logs[q], line, iserror)
                        else:
                            logname = lognames[int(iserror)]
                            logs[q] = open( logname, 'w' )      #print( 'Opening log', logname )
        
        return streams
    
    #====================================================================================================       
    def log(self, log, line, iserror):
        if self.logopen:
            self.fplog.write( line+'\n' )
        else:
            logext = '.err' if iserror else '.out'
            logname = log+logext
            print( 'Opening log', logname )
            self.fplog = open( logname, 'w' )
            self.logopen = True
            
    
    #====================================================================================================
    def active_print(self, line, iserror):
        '''a method to that intercepts output lines from the call and colourises them before printing'''
        print( line )
        #if log:
    
    #====================================================================================================
    def execute(self):
        while not self.qi.empty():                            #enqueued command(s) awaiting excecution
            s = self.qi.get()                               #grab the command as a string
            if not self.is_sentinal(s):
                print( 'EXECUTING', s )
            self.p.stdin.write( s.encode()+b'\n' )          #send the command to the subprocess as bytes string

    #====================================================================================================
    def communicate(self, command, raise_error=0, active_print=1, log=None):
        '''send command to the sub process and collect output.'''
        
        #NOTE:  THE WAY IN WHICH THE STREAM GRABBING IS CURRENTLY BEING DONE MEANS THAT THE 
        #ERROR/WARNIMG STREAM IS ONLY PRINTED AFTER THE OUTPUT STREAM - THIS MIXES UP THE ACTUAL ORDER
        # OF THE OUTPUT AS IT COMES FROM THE SUBPROCESS........
        
        if isinstance(command, (list,tuple)):
            command = ' '.join(command)
        
        self.qi.put( command )
        self.qi.put( 'echo ' + self.sentinal )                  #This is very important, without this line get_stream will never terminate!
        self.qi.put( self.error_sentinal )
        self.execute()
        
        streams = self.get_streams(active_print, log)       #Once this returns, we know the command is finished because the sentinal was reached
        output = streams[self.qo]
        error = streams[self.qe]
        
        #Error handeling
        if len(error):                                     #The command raised an error
            if raise_error:
                raise Exception( error )
            elif not active_print:
                print( 'ERROR!', error )
            
        return output
    
    send = communicate
    #====================================================================================================
    #def send(self, command, raise_error=0, active_print=1, log=None):
        #'''alias for communicate'''
        #return self.communicate( command, raise_error, active_print, log )
        
    #====================================================================================================
    def join(self):
        self.te.join()
        self.to.join()
        self.running = False

        
