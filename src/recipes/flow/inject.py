"""
Inject workers to run prior / post another function.
"""

import warnings
from collections import abc
from textwrap import dedent


class Prior:
    """Run `func(*args, **kws) after running the wrapped function."""

    def __init__(self, func, *args, **kws):
        assert callable(func)
        self.pre = func
        self.pre_args = args
        self.pre_kws = kws

    def __wrapper__(self, func, *args, **kws):
        try:
            self.pre(*self.pre_args, **self.pre_kws)
        except Exception as err:
            from recipes import pprint as pp

            warnings.warn(dedent(f'''
                Exception during pre function execution:
                {pp.caller(self.pre, self.pre_args, self.pre_kws)}
                {err}''')
                          )
        return func(*args, **kws)


class Post:
    """Run `func(*args, **kws) after running the wrapped function."""

    def __init__(self, func: abc.Callable, *args, **kws):
        assert callable(func)
        self.post = func
        self.post_args = args
        self.post_kws = kws

    def __wrapper__(self, func, *args, **kws):
        result = func(*args, **kws)
        try:
            self.post(*self.post_args, **self.post_kws)
        except Exception as err:
            from recipes import pprint as pp

            warnings.warn(dedent(f'''
                Exception during post function execution:
                {pp.caller(self.post, self.post_args, self.post_kws)}
                {err}''')
                          )
        return result
