#
#Host of useful miscellaneous classes and functions.
#
import os
import itertools as itt
import numpy as np

#from IPython import embed

class Unbuffered(object):
    '''Class to make stdout unbuffered'''
    def __init__(self, stream):
        self.stream = stream
    
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

#######################################################################################################
#measure namespace object sizes
#import sys
#from recipes.list import sortmore
#from collections import OrderedDict

#names, objects = zip(*vars().items())
#sizes = list(map(sys.getsizeof, objects))
#sizes, names = sortmore(sizes, names, order='reverse')
#sizes = OrderedDict(zip(names, sizes))
#del names, objects

import sys
from numbers import Number
from collections import Set, Mapping, deque

zero_depth_bases = (str, bytes, Number, range, bytearray)

def getsize(obj_0):
    """Recursively iterate to sum size of object & members."""
    def inner(obj, _seen_ids = set()):
        obj_id = id(obj)
        if obj_id in _seen_ids:
            return 0
        
        _seen_ids.add(obj_id)
        size = sys.getsizeof(obj)
        if isinstance(obj, zero_depth_bases):
            pass # bypass remaining control flow and return
        
        elif isinstance(obj, (tuple, list, Set, deque)):
            size += sum(inner(i) for i in obj)
        
        elif isinstance(obj, Mapping) or hasattr(obj, 'items'):
            size += sum(inner(k) + inner(v) for k, v in obj.items())
        
        # Check for custom object instances - may subclass above too
        if hasattr(obj, '__dict__'):
            size += inner(vars(obj))
        
        if hasattr(obj, '__slots__'): # can have __slots__ with __dict__
            size += sum(inner(getattr(obj, s)) for s in obj.__slots__ if hasattr(obj, s))
        
        return size
    return inner(obj_0)




#######################################################################################################
#Usefull functions
#######################################################################################################
def is_interactive():
    try:
        return bool(get_ipython().config)        #True if notebook / qtconsole
    except NameError:
        return False


class TerminalSize():
    #TODO:  split width and height searches
    #TODO:  memoize
    
    
    '''Class that returns the terminal size when called'''
    DEFAULT_WIDTH = 80
    DEFAULT_HEIGHT = 50
    
    def ioctl_GWINSZ(self, fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
        '1234'))
        except:
            return
        return cr
    
    def __call__(self):
        if is_interactive():
            # NOTE: AFAICT it's not possible to distinguish between qtconsole and notebook here
            # CHECK: QTConsole width is defined in the profile script at:  c.IPythonWidget.height
            from IPython.paths import get_ipython_dir
            from pathlib import Path
            import re
            
            path = Path(get_ipython_dir())
            profile_dir = next(path.glob('profile*'))
            config_file = next(profile_dir.glob('*config.py'))
            
            with config_file.open() as fp:
                lines = fp.read()
                #re.compile(
                w = int(re.search('c.IPythonWidget.width = (\d+)', lines).groups()[0])
                h = int(re.search('c.IPythonWidget.height = (\d+)', lines).groups()[0])
            
            return w, h
                
            #from pathlib import Path
            #from .iter import first_true_index
            #import re
            #cfile = get_ipython().config['IPKernelApp']['connection_file']
            #if isinstance(cfile, str):
                #try:    #FIXME:  THIS IS GETTING UGLY!
                    #path = Path( cfile )
                    #ix = first_true_index( path.parts, lambda s: 'profile' in s )
                    #profile_dir = Path(os.path.sep.join( path.parts[:ix+1] ))
                    #config_file = next(profile_dir.glob('*config.py'))
                    #with config_file.open() as fp:
                        #lines = fp.read()
                        #w = int(re.search( 'c.IPythonWidget.width = (\d+)', lines ).groups()[0])
                        #h = int(re.search( 'c.IPythonWidget.height = (\d+)', lines ).groups()[0])
                    #return w, h
                #except:
                    #return self.get_terminal_size()
           
                
            #else:
                #'embedded shell??'
                #return self.get_terminal_size()
        else:
            return self.get_terminal_size()
    
    def get_terminal_size(self):
        
        ioctl_GWINSZ = self.ioctl_GWINSZ
        cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
        if not cr:
            try:
                fd = os.open(os.ctermid(), os.O_RDONLY)
                cr = ioctl_GWINSZ(fd)
                os.close(fd)
            except:
                pass
        
        if not cr:
            env = os.environ
            cr = ( env.get('LINES', self.DEFAULT_HEIGHT), 
                   env.get('COLUMNS', self.DEFAULT_WIDTH) )
        
        return int(cr[1]), int(cr[0])

def getTerminalSize():
    return TerminalSize()()
    

#====================================================================================================
#attribute getter that can be curried with functools.partial
attribute_getter = lambda object, name: getattr(object, name)


def pull(obj, attr, default=None, range=()):
    '''getattr on a container of objects of same type'''
    #if range consists of np.int64/32 types, itertools throws 
    #ValueError: Stop argument for islice() must be None or an integer: 0 <= x <= sys.maxsize.
    range = map(int, range)
    return [getattr(item, attr, default) for item in itt.islice(obj,*range)]
    
    
    
    
##########################################################################################################################################   
# IPython
##########################################################################################################################################   

#====================================================================================================
def map_to_globals(var, clobber=False):
    ''' Map local variables to global variables in order to make list comprehension work in an embedded interactive shell'''
    for key, val in var.items():
        gls = globals()
        if key in gls and clobber:
            print( 'Clobbering {} in globals()'.format(key) )
        gls[key] = val
        

##########################################################################################################################################   
# Orphan functions
##########################################################################################################################################   

#CURRENTLY NOT WORKING!!!!
#====================================================================================================
def chebInterp( x, f, y, Nplims=(10,1000) ):        
    '''Chebyshev interpolation.
       x,f data points
       y - interpolation points
       Nplims - lower and upper limits for number of points to use in computation.
    '''
    
    if y.max()>x.max() or y.min()<x.min():
        print( ' WARNING! Extrapolating!' )
    
    n = len(x)
    Nl, Nu = Nplims    
    if n>Nu:
        idx = [np.argmin( np.abs(x-yp) ) for yp in y] #indices of closest matching points in x
        if np.ptp(idx)>Nu-Nl:
            print( 'SPLIT!' )
        else:
            print( 'Using points:', np.min(idx)-Nl/2, np.max(idx)+Nl/2 )
            l = slice( np.min(idx)-Nl/2, np.max(idx)+Nl/2, 1 )
            x = x[l]
            f = f[l]
    
    #scale the interval
    x /= x.max()*len(x)
    y /= y.max()*len(x)
    
    k = np.arange(len(x))    
    Tx = np.cos( np.outer(np.arccos(x),k) )    
    Ty = np.cos( np.outer(np.arccos(y),k) )    
    a = la.solve(Tx, f)    
    p = np.dot(Ty, a)    
    return p
    
