import functools
import numpy as np
import sys

##########################################################################################################################################
#Decorators
##########################################################################################################################################
class DecoratorBase(object):
    '''class based decorator with optional arguments'''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, *args, **kws):
        '''Initialization method called when '''
        self.wrapped = None
        
        # No explicit arguments provided to decorator.
        # eg.:
        # @decorator
        # def foo():
        #    ...
        if len(args) == 1 and callable(args[0]):
            func = args[0]
            self.wrapped = self.make_wrapper(func)
        
        # Explicit arguments provided to decorator.
        # eg.:
        # @decorator('hello', foo='bar')
        # def baz():
        #    ...
        else:
            #Don't know the function yet
            pass
            #inherited classes can implement stuff here
        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, *args, **kws):
        if not self.wrapped:
            self.__init__(*args, **kws)
        
        return self.wrapped(*args, **kws)
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def make_wrapper(self, func):
        #to be implemented by subclass
        raise NotImplementedError


##########################################################################################################################################
class expose():
    #TODO: OO
    #TODO: check Ipython traceback formatter?
    #TODO: Use superstring!!
    '''
    class that contains decorators for printing function arguments / content / returns
    '''
    @staticmethod
    def args(pre='', post='\n', verbosity=1):
        '''
        Decorator to print function call details - parameters names and effective values
        optional arguments specify stuff to print before and after, as well as verbosity level.
        
        Example
        -------
        @expose.args()
        def foo(a, b, c, **kw):
            return a
        
        foo('aaa', 42, id, gr=8, bar=...)
        
        prints:
        foo( a       = aaa,
             b       = 42,
             c       = <built-in function id>,
             kwargs  = {'bar': Ellipsis, 'gr': 8} )

        Out[43]: 'aaa'
        '''
        def decorator(func):
            
            @functools.wraps(func)
            def wrapper(*fargs, **fkw):
                
                fname = func.__name__       #FIXME:  does not work with classmethods
                code = func.__code__
                
                #Create a list of function argument strings
                arg_names = code.co_varnames[:code.co_argcount]
                args = fargs[:len(arg_names)]
                defaults = func.__defaults__ or ()
                args = args + defaults[len(defaults) - (code.co_argcount - len(args)):]
                
                params = list( zip(arg_names, args) )
                args = fargs[len(arg_names):]
                
                if args: 
                    params.append( ('args', args) )
                if fkw:
                    params.append( ('kwargs', fkw) )
                
                if verbosity==0:    
                    j = ', '
                elif verbosity==1:
                    j = ',\n'
                
                #Adjust leading whitespace for pretty formatting
                lead_white = [0] + [len(fname)+2] * (len(params)-1)
                trail_white = int(np.ceil(max(len(p[0]) for p in params)/8)*8)
                pars = j.join(
                    ' '*lead_white[i] + '{0[0]:<{1}}= {0[1]}'.format(p, trail_white)
                                for i,p in enumerate(params) )
                pr = '{fname}( {pars} )'.format( fname=fname, pars=pars )
                
                print( pre )
                print( pr )
                print( post )
                sys.stdout.flush()
                
                return func(*fargs, **fkw)
                
            return wrapper
            
        return decorator  

    #====================================================================================================    
    def returns():
        '''Decorator to print function return details'''
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kw):
                r = func(*args, **kw)
                print( 'RETURNING!' )
                print( r )
                return r
            return wrapper
        return decorator
    
##########################################################################################################################################
from io import StringIO

def suppress_print(func):
    '''Suppress all print statements in a function call'''
    @functools.wraps(func)
    def wrapper(*args, **kws):
        #shadow stdout temporarily
        actualstdout = sys.stdout
        sys.stdout = StringIO()
        
        r = func(*args, **kws)
        
        #restore stdout
        sys.stdout = actualstdout
        sys.stdout.flush()
        return r
    
    return wrapper

#====================================================================================================    
#def foo(a, b, c, d, e):
    #print('foo(a={}, b={}, c={}, d={}, e={})'.format(a, b, c, d, e))

#def partial_at(func, index, value):
    #@functools.wraps(func)
    #def result(*rest, **kwargs):
        #args = []
        #args.extend(rest[:index])
        #args.append(value)
        #args.extend(rest[index:])
        #return func(*args, **kwargs)
    #return result

#if __name__ == '__main__':
    #bar = partial_at(foo, 2, 'C')
    #bar('A', 'B', 'D', 'E') 
    # Prints: foo(a=A, b=B, c=C, d=D, e=E)

def partial_at(func, indices, *args):
    '''Partial function application for arguments at given indices.'''
    @functools.wraps( func )
    def wrapper( *fargs, **fkwargs ):
        nargs = len(args) + len(fargs)
        iargs = iter(args)
        ifargs = iter(fargs)
        
        posargs = ( next((ifargs, iargs)[i in indices]) for i in range(nargs) )
        #posargs = list( posargs )
        #print( 'posargs', posargs )
        
        
        return func(*posargs, **fkwargs)
        
    return wrapper
    
#====================================================================================================    
def starwrap( func ):
    def wrapper(args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

#====================================================================================================  
# Code profiling
from line_profiler import LineProfiler

#class Profile(object):
    #'''Wrapper for code profiling.'''
    #def __call__(self, follow=[]):
        

def profile( follow=[] ):
    '''Wrapper for code profiling.'''
    def decorator(func):
        @functools.wraps(func)
        def profiled_func(*args, **kwargs):
            try:
                profiler = LineProfiler()
                profiler.add_function(func)
                for f in follow:
                    profiler.add_function(f)
                profiler.enable_by_count()
                return func(*args, **kwargs)
            finally:
                profiler.print_stats()
        return profiled_func
        
    return decorator

#except ImportError:
    #def do_profile(follow=[]):
        #"Helpful if you accidentally leave in production!"
        #def inner(func):
            #def nothing(*args, **kwargs):
                #return func(*args, **kwargs)
            #return nothing
        #return inner
        
#====================================================================================================
#decorator to convert posix paths to strings
#TODO:  Make this decorator more general?  Type conversion
from pathlib import Path
class path():
    '''class that contains decorators for operating on pathlib.Path objects'''
    class to_string():
        #def __call__(self):
            #return 
            
        @staticmethod
        def at(*where):
            '''
            Decorator (factory) to auto-convert arguments to strings.
            Intended to be used for converting pathlib.Path to strings
            Useful when (for example) a variable is expected to be a string by the function
            internals.  With this decorator they can now also be pathlib.Path objects.
            
            Example
            -------
            path = Path('/media/Oceanus/Observing/data/')
            path_conversion()(np.loadtxt)(path, 0)
            '''
            if not len(where):
                where = (0,)    #default to convert first argument
                
            def deco(func):

                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    nargs = tuple( str(arg)     if i in where       else arg
                                        for i,arg in enumerate(args) )  #convert the specified arg to string
                    return func(*nargs, **kwargs)       #return the function

                return wrapper

            return deco
        
        @staticmethod
        def auto( func ):
            '''
            Example
            -------
            @path.to_string.auto
            def foo(a, b, c, **kw):
                print(a)
            foo(Path('/home/hannes'), 2, 3)
            '''
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                nargs = tuple( str(a) if isinstance(a,Path) else a 
                                for a in args )
                nkws =  { key : str(val) if isinstance(val,Path) else val 
                            for key, val in kwargs.items() }
                return func(*nargs, **nkws)
            return wrapper
        

#====================================================================================================  
# PyQt
#from PyQt4.QtCore import pyqtRemoveInputHook, pyqtRestoreInputHook
def unhookPyQt(func):
    '''Decorator that removes the PyQt input hook during the execution of the decorated function.
    Used for functions that need ipython / terminal input prompts to work with pyQt.'''
    @functools.wraps(func)
    def unhooked_func(*args, **kwargs):
        pyqtRemoveInputHook()
        out = func(*args, **kwargs)
        pyqtRestoreInputHook()
        return out
    
    return unhooked_func

#====================================================================================================  
# memoization
import json
import atexit
import functools
from pathlib import Path

def persistant_memoizer(filename, verbose=True):
    '''memoizer that saves cache to file at program termination'''
    filepath = Path(filename)
    if filepath.exists():
        #load existing cache
        if verbose:
            print('loading cache at', str(filepath))
        with filepath.open('r') as fp:
            cache = json.load(fp)
            #dict(map(tuple, kv) for kv in json.loads(on_disk))
    else:
        #no existing cache. create
        if verbose:
            print('creating cache at', str(filepath))
        cache = {}
    
    #Setup save function
    def save_cache(filename):
        '''save function cache to file'''
        if verbose:
            print('saving cache at', str(filepath), cache)
        with filepath.open('w') as fp:
            json.dump(cache, fp)
        
    atexit.register(save_cache, filename) #NOTE: will not be saved on unnatural exit
    
    #create decorator
    def decorator(func):
        
        @functools.wraps(func)
        def memoizer(*args):  #NOTE: DOES NOT SUPPORT KEYWORDS#, **kws):
            #NOTE: it is generally impossible to correctly memoize something that depends on non-hashable arguments
            #convert to string
            key = str(args)# + str(kws)
            if key not in cache:
                cache[key] = func(*args)#, **kws)
            return cache[key]
        
        return memoizer
    
    return decorator

#====================================================================================================  
def cache_last_return(obj):
    #cache = obj.cache = None

    @functools.wraps(obj)
    def wrapper(*args, **kwargs):
        #print( obj )
        wrapper.cache = obj(*args, **kwargs)
        return wrapper.cache
    return wrapper

#====================================================================================================  
def cache_returns(obj):
    cache = obj.cache = []
    #def decorator(func):
    @functools.wraps(obj)
    def wrapper(*args, **kwargs):
        #print( obj )
        
        wrapper.cache.append( obj(*args, **kwargs) )
        return wrapper.cache[-1]
    return wrapper


#====================================================================================================  
def upon_first_call( do_first ):
    def decorator(func):

        def wrapper(self, *args, **kwargs):
            if not wrapper.has_run:
                wrapper.has_run = True
                do_first( self )
            return func(self, *args, **kwargs)
        
        wrapper.has_run = False
        return wrapper
    
    return decorator

#def do_first(q):
    #print( 'DOING IT', q )

#class Test(object):
    
    #@upon_first_call( do_first )
    #def bar( self, *args ) :
        #print( "normal call:", args )

#test = Test()
#test.bar()
#test.bar()


def trydec(func):
    #TODO: a more informative name
    #TODO: change the kernel banner
    #TODO: print the full traceback
    #TODO: save and import the local namespace of the decorated function
    '''
    @trydec
    def foo():
        raise ValueError( 'FUCK!' )
    
    foo()               #will embed a kernel here
    '''
    @functools.wraps( func )
    def wrapper( *fargs, **fkwargs ):
        try:
            return func(*fargs, **fkwargs)
        except Exception as err:
            print( err )
            embed()
    return wrapper
