"""
Miscellaneous decorators
"""

from .base import OptionalArgumentsDecorator
from .expose import SameLineDone#, #InfoPrintWrapper

##########################################################################################################################################
def optional_arg_decorator(func):           #TODO as a class
    """Generic decorator decorator code"""
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
    """
    A decorator that can handle optional keyword arguments.

    When the decorator is called with no optional arguments like this:

    @decorator
    def function ...

    The function is passed as the first argument and decorate returns the decorated function, as expected.

    If the decorator is called with one or more optional arguments like this:

    @decorator(optional_argument1='some value')
    def function ....

    Then decorator is called with the function argument with value None, so a function that decorates
    is returned, as expected.
    """
    #print('WHOOP', func, dkws)
    def _decorate(func):

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
    """Partial function application for arguments at given indices."""
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
    """
    Decorator that removes the PyQt input hook during the execution of the decorated function.
    Used for functions that need ipython / terminal input prompts to work with pyQt.
    """
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



import atexit
import functools
from pathlib import Path

from recipes.io import load_pickle, save_pickle

class persistant_memoizer():
    """memoizer that saves cache to file upon program termination"""

    def __init__(self, filename, verbose=True):  # TODO: use decoratorbase here?
        filepath = Path(filename).expanduser()
        filename = str(filepath)
        decorator = SameLineDone if verbose else OptionalArgumentsDecorator
        create_cache = decorator('Creating cache at %s' % filename)(lambda: {})
        load_cache = decorator('Loading cache at %s' % filename, 'Done')(load_pickle)
        self._save_cache = decorator('Saving cache at %s\n' % filename, 'Done')(save_pickle)

        if filepath.exists():
            # load existing cache
            self._cache = load_cache(filename)
            if verbose:
                print('Cache contains %d entries' % len(self._cache))
        else:
            # no existing cache. create.  this will only happen the first time the function executes
            self._cache = create_cache()

        self._save = False
        atexit.register(self.save, filename, self._cache)  # NOTE: will not be saved on unnatural exit

    def save(self, filename, cache):
        if self._save:
            self._save_cache(filename, cache)

    def __call__(self, func):
        @functools.wraps(func)
        def memoizer(*args):
            # NOTE: DOES NOT SUPPORT KEYWORDS#, **kws):
            # NOTE: it is generally impossible to correctly memoize something that depends on non-hashable arguments
            # convert to string
            key = str(args)  # + str(kws)     #isinstance(args, Hashable)
            if key not in self._cache:
                self._cache[key] = func(*args)  # , **kws)
                self._save = True
            return self._cache[key]

        return memoizer





class memoize():
    """
    Decorator that caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
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
        """Return the function's docstring."""
        return self.func.__doc__

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    to_file = persistant_memoizer

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
    """
    @trydec
    def foo():
        raise ValueError( 'FUCK!' )

    foo()               #will embed a kernel here
    """
    @functools.wraps( func )
    def wrapper( *fargs, **fkwargs ):
        try:
            return func(*fargs, **fkwargs)
        except Exception as err:
            print( err )
            embed()
    return wrapper
