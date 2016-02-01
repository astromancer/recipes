import functools
import numpy as np
import sys

##########################################################################################################################################
#Decorators
##########################################################################################################################################
class Wrapper(object):
    '''Decorator to print function return details'''
    def __init__(self, *args, **kws):
        print( 'initializing' )
        self.args = args
        self.kws = kws
      
class  print_returns( Wrapper ):
    def __call__(self, func):
        print( 'calling!' )
        
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            #print( "In my decorator before call, with arg", self.args )
            r = func(*args, **kwargs)
            print( 'Returning:\n', r )
            return r

        return decorated

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
from PyQt4.QtCore import pyqtRemoveInputHook, pyqtRestoreInputHook
def unhookPyQt( func ):
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
def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer

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
def upon_first_call( do_first ):
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
