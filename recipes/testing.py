import inspect
import textwrap
from collections import defaultdict

import pytest


# FIXME: get this to work inside a class!!
# FIXME: deal with unhashable arguments
#       slice, set, list, dict, array
# TODO: expected decorator

# @expected(
#     (CAL/'SHA_20200822.0005.fits', shocBiasHDU,
#      CAL/'SHA_20200801.0001.fits', shocFlatHDU,
#      EX1/'SHA_20200731.0022.fits', shocNewHDU)
# )
# def hdu_type(filename):
#     return _BaseHDU.readfrom(filename).__class__

def to_tuple(x):
    if not isinstance(x, tuple):
        return (x, )
    return x

class expected:
    def __init__(self, items, *args, **kws):
        self.items = items
        self.args = args
        self.kws = kws

    def __call__(self, func):
        return Expect(func)(self.items, *self.args, **self.kws)

        # return pytest.mark.parametrize(
        #     names, self.items, *self.args, **self.kws)(func)


# class ArgSpec:
#     def __init__(self, func, args):
#         self.func = func
#         self.args = args


# class TestMaker:

#     def __init__(self, func):
#         # self.signatures = {}
#         # for f in funcs:
#         self.func = func
#         self.sig = inspect.signature(func)
#         # setattr(self, f.__name__, self.make_args(f))

#     def __call__(self, *args, **kws):
#         ba = self.sig.bind(*args, **kws)
#         ba.apply_defaults()
#         return ArgSpec(self.func, ba.arguments.items())

#     def make_test(self):
#         args = ', '.join(self.sig.parameters.keys())
#         name = self.func.__name__
#         test_name = f'test_{name}'

#         code = textwrap.dedent(
#             f'''
#             global {test_name}
#             def {test_name}({args}, output):
#                 assert {name}({args}) == output
#             ''')
#         return code


class Expect(object):
    """
    Testing helper for checking expected return values for functions. Allows
    one to build simple paramertized tests of complex function without needing
    to explicitly type an exhaustive combination of exact function parameters
    (of which there may be many)

    For example, to test that the function `decimal` returns the expected
    values, do the following:
    >>> ex = Expect(decimal)(
    ...         {1e4:             '10000.0',
    ...          0.0000123444:    '0.0000123'},
    ...         globals()))

    This will automatically construct a test: 'test_dicimal' which has the same
    signature as the function `decimal`. The the sequence of input output pairs
    passed to the `expects` method is used to parametrize the test, so that
    pytet will include all cases in your test run
    """

    def __init__(self, func):
        self.func = func
        self.sig = inspect.signature(func)
        self.is_method = (func.__name__ != func.__qualname__)
        self.test_name, self.test_code = self.make_test(func)
        setattr(self, func.__name__, self.bind)

    def bind(self, *args, **kws):
        ba = self.sig.bind(*args, **kws)
        ba.apply_defaults()
        return ba

    def __call__(self, items, *args, globals_=None, locals_=None, **kws):
        #
        if isinstance(items, dict):
            items = items.items()

        return self.expects(items, *args, **kws,
                            globals_=globals_, locals_=locals_)


    def expects(self, items, *args,  globals_=None, locals_=None, **kws):
        names, values = self.get_names_values(items)

        # test_name, code = self.make_test(func, globals_ is None)
        locals_ = {}

        from IPython import embed
        embed(header="Embedded interpreter at 'testing.py':119")


        exec(self.test_code, globals_, locals_)
        # print(locals_, test_name, globals_) # (locals_[test_name])
        lookup = globals_ or locals_

        test = lookup[self.test_name]
        return pytest.mark.parametrize(names, values, *args, **kws)(test)

    def get_names_values(self, items):
        values = defaultdict(list)
        expected = []
        for args, answer in items:
            expected.append(answer)

            if not isinstance(args, inspect.BoundArguments):
                args = (None,) * self.is_method + to_tuple(args)
                args = self.bind(*args)

            for name, val in tuple(args.arguments.items())[self.is_method:]:
                values[name].append(val)

        names = tuple(values.keys()) + ('output', )
        values = zip(*values.values(), expected)
        return names, values

    def make_test(self, func, gflag=True):
        args = ", ".join(self.sig.parameters.keys())
        name = func.__name__
        test_name = f'test_{name}'
        gline = f'global {test_name}' if gflag else ''

        # assert test_name not in globals()

        code = textwrap.dedent(
            f'''
            {gline}
            def {test_name}({args}, output):
                assert {name}({args}) == output
            ''')
        return test_name, code
