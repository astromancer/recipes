"""
Base classes for extensible decorators.
"""

import types
import functools as ftl
import logging


logging.basicConfig()
logger = logging.getLogger(__file__)


def inclass(meth):
    return '.' in str(meth)


class DecoratorBase:
    """
    A picklable decorator. Does nothing by default.
    """

    def __init__(self, func):
        self.func = func
        # Update this class to look like the wrapped function
        ftl.update_wrapper(self, func)

    def __call__(self, *args, **kws):
        # Default null decorator
        return self.func(*args, **kws)


class decorator:
    """
    Decorator class with optional arguments. Can be pickle, unlike function
    based decorators / factory.

    There are two distinct use cases
    1) No explicit arguments provided to decorator.
    eg.:

    >>> @decorator
    ... def foo():
    ...    return 'did something'

    In this case the wrapper will be built upon construction in `__new__`

    2) Explicit arguments and/or keywords provided to decorator.
    eg.:

    >>> @decorator('hello', foo='bar')
    ... def baz(*args, **kws):
    ...    ...

    In this case the wrapper will be built upon first call to function

    This is an abstract class in that it does nothing by default. Let's make it
    usefull:
    class increment(decorator):
        def wrapper(self, func)
            return self.func(*args, **kws) + 1



    NOTE: The use case above is identified based on the type of object the
        constructor receives. It is therefore not possible to use this decorator
        if the first argument to the decorator initializer is a function.

        Like so:
        >>> @decorator(some_callable) # will not work as indended
        ... def buz():
        ...     ...

        Purists might argue that this class is an anti-pattern since it invites
        less explicit constructs that are confusing to the uninitiated.
        Here it is. Use it. Don't use it. Up to you.
)

    """
    func = None

    def __init__(self, *args, **kws):
        """
        Inherited classes can implement stuff here, for example do something
        with the `args` and `kws`
        """

        if len(args) == 1 and callable(args[0]):
            # No arguments provided to decorator.
            # @decorator
            # def foo():
            #    return 'did something'
            # No initialization necessary
            super().__init__()
            self.wrap(args[0])
        else:
            # Explicit arguments and/or keywords provided to decorator.
            # @decorator('hello world!')
            # def foo():
            #    return 'did something'
            # Initialize with args
            print('RECURSE', args, kws)
            super(Decorator, self).__init__(*args, **kws)

    def __call__(self, *args, **kws):
        if self.func is None:
            # The wrapped function has not yet been created - arguments passed
            # to decorator constructor
            self.wrap(args[0])  # make the wrapped function
            return self  #

        # The wrapped function has already been created
        return self.wrapper(*args, **kws)  # call the wrapped function

    def wrapper(self, *args, **kws):
        return self.func(*args, **kws)

    def wrap(self, func):
        """Null wrapper. To be implemented by subclass"""

        # for decorated methods: make wrapped function MethodType to avoid
        # errors downstream
        # if inclass(func):
        #     # FIXME: binds to the wrong class!!
        #       at build time this function is still unbound!
        #     func = types.MethodType(func, self)

        # update __call__ method to look like func
        ftl.update_wrapper(self, func)
        self.func = func


# alias
Decorator = decorator


class DecorMeta(type):
    'todo'

class OptArgDecor:

    def __new__(cls, *args, **kws):
        logger.debug('__new__ %s: %s; %s', cls, args, kws)
        obj = object.__new__(cls)

        if len(args) == 1 and callable(args[0]):
            # No optional arguments provided to decorator.
            # eg. usage:
            # @decorator
            # def foo(): pass
            logger.debug('No explicit arguments provided to decorator')
            func = args[0]
            cls.__init__(obj)
            obj.wrapped = obj.make_wrapper(func)
        else:
            obj.wrapped = None
            # (optional) arguments provided to decorator.
            # eg. usage:
            # @decorator('hello world', bar=None)
            # def foo(): pass
            logger.debug('Arguments given: %s; %s', args, kws)
            # Don't know the function yet, so can't create the wrapper
            # will create wrapper upon __call__

        return obj

    def __init__(self, *args, **kws):
        """
        Inherited classes can implement stuff here, for example what to do with
        the args and kws passed to the constructor
        """
        logger.debug('__init__ %s: %s; %s', self, args, kws)
        # if self.wrapped is None:

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, *args, **kws):
        logger.debug('calling with %s; %s', args, kws)

        if self.wrapped is None:
            # The wrapped function has not yet been created - arguments passed
            # to decorator constructor
            logger.debug('not wrapped yet. creating wrapper. args: %s; kws: %s',
                    args, kws)
            func=args[0]
            return self.make_wrapper(func)  # return the wrapped function

        # The wrapped function has already been created
        logger.debug('calling wrapped %s %s %s', self, args, kws)
        return self.wrapped(*args, **kws)  # call the wrapped function

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def make_wrapper(self, func):
        """Null wrapper. To be implemented by subclass"""
        logger.debug('wrapping %s', func)
        # logger.debug(('!'*10)+str(getattr(func, '__self__', None)))

        # for decorated methods: make wrapped function MethodType to avoid
        # errors downstream
        if inclass(func):
            func=types.MethodType(func, self)

        # update __call__ method to look like func
        ftl.update_wrapper(self, func)

        return func


#%%
class count_calls(OptArgDecor):
    def __init__(self, start=0, inc=1):
        self.count = start
        self.inc = inc
    
    def wrapper(self, *args, **kws):
        result = self.func(*args)
        self.count += self.inc
# %%
