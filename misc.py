import functools
import numpy as np
import sys

##########################################################################################################################################
#Decorators
##########################################################################################################################################
#TODO: MAYBE TRY USE NEW??
#If __new__() does not return an instance of cls, then the new instance's __init__() method will not be invoked.
#TODO: or implement this as a factory??

class DecoratorBase(object):
    '''class based decorator with optional arguments'''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, *args, **kws):               #OR use NEW??
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
            self.setup(*args, **kwargs)
        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, *args, **kws):
        if not self.wrapped:
            self.__init__(*args, **kws)
            return self.wrapped
            
        return self.wrapped(*args, **kws)
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def make_wrapper(self, func):
        #to be implemented by subclass
        raise NotImplementedError
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def setup(self, *args, **kwargs):
        #inherited classes can implement stuff here
        pass
    
    
##########################################################################################################################################
#class print_returns(DecoratorBase):
    #def setup(self, *args, **kws):
        #how = args[0]
    
    #def make_wrapper(self, func):
        #@functools.wraps(func)
        #def wrapper(*args, **kw):
            #r = func(*args, **kw)
            #print( 'RETURNING!' )
            #print( r )
            #return r
        #return wrapper


##########################################################################################################################################
def optional_arg_decorator(func):           #TODO as a class
    '''Generic decorator decorator code'''
   
    def wrapped_decorator(*args):
        if len(args) == 1 and callable(args[0]):
            return func(args[0])

        else:
            def real_decorator(decoratee):
                return func(decoratee, *args)

            return real_decorator

    return wrapped_decorator


##########################################################################################################################################
def decorator_with_keywords(func=None, **dkws):
    #NOTE:  ONLY ACCEPTS KW ARGS
    '''
    A decorator that can handle optional keyword arguments.
    
    When the decorator is called with no optional arguments like this:

    @decorator
    def function ...
    
    The function is passed as the first argument and decorate returns the decorated function, as expected.

    If the decorator is called with one or more optional arguments like this:

    @decorator(optional_argument1='some value')
    def function ....
    
    Then decorator is called with the function argument with value None, so a function that decorates is returned, as expected.
    '''
    
    #print('WHOOP', func, dkws)
    
    def _decorate(function):

        @functools.wraps(func)
        def wrapped_function(*args, **kws):
            #print('!!')
            return func(*args, **kws)
            
        return wrapped_function

    if func:
        return _decorate(func)

    return _decorate



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
def starwrap(func):
    def wrapper(args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

#====================================================================================================  
# PyQt
from PyQt5.QtCore import pyqtRemoveInputHook, pyqtRestoreInputHook
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
# memoize
#def memoize(obj):
    #cache = obj.cache = {}

    #@functools.wraps(obj)
    #def memoizer(*args, **kwargs):
        #key = str(args) + str(kwargs)
        #if key not in cache:
            #cache[key] = obj(*args, **kwargs)
        #return cache[key]
    #return memoizer



import json
import atexit
import functools
from pathlib import Path
#from collections import Hashable

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
            key = str(args)# + str(kws)     #isinstance(args, Hashable)
            if key not in cache:
                cache[key] = func(*args)#, **kws)
            return cache[key]
        
        return memoizer
    
    return decorator




#def persist_to_file(file_name):

    #def decorator(original_func):

        #try:
            #cache = json.load(open(file_name, 'r'))
        #except (IOError, ValueError):
            #cache = {}

        #def new_func(param):
            #if param not in cache:
                #cache[param] = original_func(param)
                #json.dump(cache, open(file_name, 'w'))
            #return cache[param]

        #return new_func

    #return decorator



    
class memoize():
    '''
    Decorator that caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    '''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    def __init__(self, func):
      self.func = func   #can also be a method?
      self.cache = {}
      
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    def __call__(self, *args, **kws):
        
        #if not isinstance(args, collections.Hashable):
            ## uncacheable. a list, for instance.
            ## better to not cache than blow up.
            #return self.func(*args)
        
        #arguments may not be hashable. Convert them to strings first.
        #WARNING: This will not work for objects that do not have unique string representations
        key = str(args) + str(kws)
            
        if key in self.cache:
            return self.cache[key]
        else:
            value = self.func(*args)
            self.cache[key] = value
            return value
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    def __repr__(self):
        '''Return the function's docstring.'''
        return self.func.__doc__
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    def __get__(self, obj, objtype):
        '''Support instance methods.'''
        return functools.partial(self.__call__, obj)
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    @staticmethod
    def to_file(filename):      #TODO:  THIS CAN BE HANDELED BY OPTIONAL ARGUMENTS!!!!!
        import json
        #====================================================================================================    
        def decorator(func):
            
            try:
                cache = json.load(open(filename, 'r'))
            except (IOError, ValueError):
                cache = {}
            
            @functools.wraps(func)
            def memoizer(*args, **kws):
                #NOTE: it is generally impossible to correctly memoize something that depends on non-hashable arguments
                #convert to string
                key = str(args) + str(kwargs)
                if key not in cache:
                    cache[key] = func(*args, **kwargs)
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
    #def actualDecorator(func):
    @functools.wraps(obj)
    def wrapper(*args, **kwargs):
        #print( obj )
        
        wrapper.cache.append( obj(*args, **kwargs) )
        return wrapper.cache[-1]
    return wrapper


#====================================================================================================  
def upon_first_call(do_first):
    def actualDecorator(func):

        def wrapper(self, *args, **kwargs):
            if not wrapper.has_run:
                wrapper.has_run = True
                do_first( self )
            return func(self, *args, **kwargs)
        
        wrapper.has_run = False
        return wrapper
    
    return actualDecorator

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
