"""
Miscellaneous decorators
"""


# TODO add usage patterns to all these classes!!!


import functools


class singleton:
    # adapted from:
    # https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html
    def __init__(self, klass):
        self.klass = klass
        self.instance = None

    def __call__(self, *args, **kws):
        if self.instance is None:
            self.instance = self.klass(*args, **kws)
        return self.instance


def optional_arg_decorator(func):  # TODO as a class
    """Generic decorator decorator code"""
    # won't work on objects that expect callables as a first argument ??
    def wrapped_decorator(*args):
        if len(args) == 1 and callable(args[0]):
            return func(args[0])

        else:
            def real_decorator(decoratee):
                return func(decoratee, *args)

            return real_decorator

    return wrapped_decorator


def decorator_with_keywords(func=None, **dkws):
    # NOTE:  ONLY ACCEPTS KW ARGS
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

    # print('WHOOP', func, dkws)
    def _decorate(func):
        @functools.wraps(func)
        def wrapped_function(*args, **kws):
            # print('!!')
            return func(*args, **kws)

        return wrapped_function

    if func:
        return _decorate(func)

    return _decorate



# bar = partial_at(foo, 2, 'C')
# bar('A', 'B', 'D', 'E')
# Prints: foo(a=A, b=B, c=C, d=D, e=E)

def partial_at(func, indices, *args):
    """Partial function application for arguments at given indices."""

    @functools.wraps(func)
    def wrapper(*fargs, **fkwargs):
        nargs = len(args) + len(fargs)
        iargs = iter(args)
        ifargs = iter(fargs)

        posargs = (next((ifargs, iargs)[i in indices]) for i in range(nargs))
        # posargs = list( posargs )
        # print( 'posargs', posargs )

        return func(*posargs, **fkwargs)

    return wrapper


def starwrap(func):
    def wrapper(args, **kwargs):
        return func(*args, **kwargs)

    return wrapper



def upon_first_call(do_first):
    def actualDecorator(func):
        def wrapper(self, *args, **kwargs):
            if not wrapper.has_run:
                wrapper.has_run = True
                do_first(self)
            return func(self, *args, **kwargs)

        wrapper.has_run = False
        return wrapper

    return actualDecorator

# def do_first(q):
# print( 'DOING IT', q )

# class Test:

# @upon_first_call( do_first )
# def bar( self, *args ) :
# print( "normal call:", args )

# test = Test()
# test.bar()
# test.bar()
