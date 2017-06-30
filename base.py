"""
Base class for extensible decorators
"""

import functools
import logging

# logging.basicConfig(level=logging.DEBUG)

#====================================================================================================
class DecoratorBase():
    '''A picklable decorator'''
    def __init__(self, func):
        self.func = func
        # Update this class to look like the wrapped function
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kws):
        # Default null decorator
        return self.func(*args, **kws)


class OptionalArgumentsDecorator(object):
    # FIXME: does not work with methods......
    """
    Decorator class with optional arguments. Can be pickled, unlike function based decorators.
    """

    # TODO: MAYBE TRY USE __new__??
    # If __new__() does not return an instance of cls, then the new instance's __init__() method will not be invoked.
    # TODO: or implement this as a factory??
    def __new__(cls, *args, **kws):
        logging.debug('__new__ %s: %s; %s' %(cls, args, kws))
        return object.__new__(cls)  # using "object" avoids recursion

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, *args, **kws):               #TODO: OR use __new__ ??
        """
        Initialize our decorator.  There are two distinct use cases
        1) No explicit arguments provided to decorator.
        eg.:
        @decorator
        def foo():
           ...
        In this case the wrapper will be built upon initialization here

        2) Explicit arguments and/or keywords provided to decorator.
        eg.:
        @decorator('hello', foo='bar')
        def baz():
            ...
        In this case the wrapper will be built upon first call to function
        """
        logging.debug('initializing with %s; %s' %(args, kws))

        # No explicit arguments provided to decorator.
        if len(args) == 1 and callable(args[0]):
            logging.debug('No explicit arguments provided to decorator')
            func = args[0]
            self.setup()    # use default arguments for setup
            self.wrapped = self.make_wrapper(func)

        # (optional) arguments provided to decorator.
        else:
            # Don't know the function yet, so can't create the wrapper
            logging.debug('Arguments given: %s; %s' %(args, kws))
            self.setup(*args, **kws)
            self.wrapped = None         # will create wrapper upon __call__

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, *args, **kws):
        if not self.wrapped:
            # The wrapped function has not yet been created - arguments passed to decorator constructor
            logging.debug('not wrapped yet. creating wrapper. args: %s; kws: %s' %(args, kws))
            func = args[0]
            return self.make_wrapper(func)  # return the wrapped function

        # The wrapped function has already been created
        logging.debug('calling wrapped %s %s %s' %(self, args, kws))
        return self.wrapped(*args, **kws)   # call the wrapped function

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def make_wrapper(self, func):
        """Null wrapper. To be implemented by subclass"""
        logging.debug('wrapping %s' %func)
        # functools.wraps(func)
        return func

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def setup(self, *args, **kws):
        """
        This is really the initialization method for the decorator.  Inherited classes can implement
        stuff here, for example what to do with the args and kws passed to the constructor
        """
        pass


if __name__ == '__main__':

    @OptionalArgumentsDecorator
    def foo1():
        print('foo1')

    @OptionalArgumentsDecorator()
    def foo2():
        print('foo2')


    class Foo():
        @OptionalArgumentsDecorator
        def method1(self):
            print('method1')

        @OptionalArgumentsDecorator()
        def method2(self):
            print('method2')

    # try:
    #     # foo1()
    #     # foo2()
    #
    #     foo = Foo()
    #     foo.method1()
    #     # foo.method2()
    # except:


    # from IPython import embed
    # embed()