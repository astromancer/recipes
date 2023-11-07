

# std
import functools as ftl

# relative
from .base import Decorator


# ---------------------------------------------------------------------------- #
class delayed(Decorator):

    def __wrapper__(self, func, *args, **kws):
        return ftl.partial(func, *args, **kws)


# ---------------------------------------------------------------------------- #
class update_defaults(Decorator):

    def __init__(self, mapping=(), **kws):
        self.defaults = dict(mapping, **kws)

    def __call__(self, func, kwsyntax=False):

        code = func.__code__
        param_names = code.co_varnames[:code.co_argcount]
        defaults = {}
        if current_defaults := func.__defaults__:
            defaults.update(
                zip(param_names[-len(current_defaults):], current_defaults)
            )
        defaults.update(self.defaults)

        func.__defaults__ = tuple(defaults.pop(name)
                                  for name in param_names if name in defaults)

        if defaults:
            func.__kwdefaults__ = {**(func.__kwdefaults__ or {}), **defaults}

        #                             emulate
        return super().__call__(func, True, kwsyntax)


# ---------------------------------------------------------------------------- #
def ignore_params(func):

    @ftl.wraps(func)
    def wrapper(*_, **__):
        return func()

    return wrapper


def ignore_returned(func):

    @ftl.wraps(func)
    def wrapper(*args, **kws):
        func(*args, **kws)

    return wrapper


ignore_returns = ignore_returned

# ---------------------------------------------------------------------------- #
# TODO add usage patterns to all these classes!!!


def upon_first_call(do_first):

    def decorator(func):
        func._ran = False

        def wrapper(self, *args, **kwargs):
            if not func._ran:
                do_first(self)

            results = func(self, *args, **kwargs)
            func._ran = True
            return results

        return wrapper

    return decorator

# def do_first(q):
# print( 'DOING IT', q )

# class Test:

# @upon_first_call( do_first )
# def bar( self, *args ) :
# print( "normal call:", args )

# test = Test()
# test.bar()
# test.bar()
