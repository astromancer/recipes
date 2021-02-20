import inspect
import textwrap
from collections import defaultdict

import pytest


# FIXME: get this to work inside a class!!

# TODO: expected decorator

# @expected(
#     (CAL/'SHA_20200822.0005.fits', shocBiasHDU,
#      CAL/'SHA_20200801.0001.fits', shocFlatHDU,
#      EX1/'SHA_20200731.0022.fits', shocNewHDU)
# )
# def hdu_type(filename):
#     return _BaseHDU.readfrom(filename).__class__

def echo(*args, **kws):
    return args, tuple(kws.items())


class WrapArgs:
    def __init__(self, *args, **kws):
        self.args = args
        self.kws = tuple(kws.items())

    def __iter__(self):
        return iter((self.args, self.kws))


class Mock:
    def __getattr__(self, _):
        return WrapArgs


mock = Mock()
# wrap_args = WrapArgs()

# test_hms = Expect(hms).expects(
#     {mock.hms(1e4):  '02h46m40.0s',
#      mock.hms(1.333121112e2, 5): '00h02m13.31211s',
#      mock.hms(1.333121112e2, 5, ':'):  '00:02:13.31211',
#      mock.hms(1.333121112e2, 5, short=False): '00h02m13.31211s',
#      mock.hms(1.333121112e2, 'm0', short=False, unicode=True): '00ʰ02ᵐ',
#      mock.hms(119.95, 's0'): '00h02m00s',
#      mock.hms(1000, 'm0', sep=':'): '00:17',
#      #  ex.hms(1e4, sep='', sig=0, sign='+'):  '024640'
#      }
# )


class expected:
    """
    Examples
    --------
    >>> @expected(
            # test input                   # expected result 
    ...     (CAL/'SHA_20200822.0005.fits', shocBiasHDU,
    ...      CAL/'SHA_20200801.0001.fits', shocFlatHDU,
    ...      EX1/'SHA_20200731.0022.fits', shocNewHDU)
    ... )
    ... def hdu_type(filename):
    ...     return _BaseHDU.readfrom(filename).__class__
    """

    def __init__(self, items, *args, **kws):
        self.items = items
        self.args = args
        self.kws = kws

    def __call__(self, func):
        return Expect(func)(self.items, *self.args, **self.kws)


class Expect:
    """
    Testing helper for checking expected return values for functions. Allows
    one to build simple paramertized tests of complex function without needing
    to explicitly type an exhaustive combination of exact function parameters
    (of which there may be many)

    For example, to test that the function `hms` returns the expected
    values, do the following:
    >>> ex = Expect(hms)
    >>> test_hms = ex.expects(
            {ex.hms(1e4):  '02h46m40.0s',
             ex.hms(1.333121112e2, 5): '00h02m13.31211s',
             ex.hms(1.333121112e2, 5, ':'):  '00:02:13.31211',
             ex.hms(1.333121112e2, 5, short=False): '00h02m13.31211s',
             ex.hms(1.333121112e2, 'm0', short=False, unicode=True): '00ʰ02ᵐ',
             ex.hms(119.95, 's0'): '00h02m00s',
             ex.hms(1000, 'm0', sep=':'): '00:17',
            }
        )

    This will automatically construct a test: 'test_dicimal' which has the same
    signature as the function `decimal`. The sequence of input output pairs
    passed to the `expects` method is used to parametrize the test, so that
    pytest will include all cases in your test run. Assigning the output of the
    `expects` method above to a variable name starting with 'test_' is important
    for pytest test discovery to work correctly.
    """

    def __init__(self, func):
        self.func = func
        self.sig = inspect.signature(func)
        # crude test for whether this function is defined in a class scope
        self.is_method = (func.__name__ != func.__qualname__)
        self.test_name, self.test_code = self.make_test(func)
        setattr(self, func.__name__, self.echo)

    def echo(self, *args, **kws):
        return args, tuple(kws.items())

    def bind(self, *args, **kws):
        ba = self.sig.bind(*args, **kws)
        ba.apply_defaults()
        return ba

    def __call__(self, items, *args, **kws):
        return self.expects(items, *args, **kws)

    def expects(self, items, *args, **kws):

        if isinstance(items, dict):
            items = items.items()

        # parse the arguments
        names, values = self.get_names_values(items)

        # create the test
        locals_ = {}
        exec(self.test_code, None, locals_)
        #test = eval(self.test_name)
        test = locals_[self.test_name]
        return pytest.mark.parametrize(names, values, *args, **kws)(test)

    def get_names_values(self, items):
        values = defaultdict(list)
        expected = []
        for spec, answer in items:
            expected.append(answer)

            if not isinstance(spec, WrapArgs):
                # simple construction without use of mock function
                spec = WrapArgs(spec)

            args, kws = spec
            args = (None,) * self.is_method + args
            ba = self.bind(*args, **dict(kws))

            for name, val in tuple(ba.arguments.items())[self.is_method:]:
                values[name].append(val)

        names = tuple(values.keys()) + ('output', )
        values = tuple(zip(*values.values(), expected))
        return names, values

    def make_test(self, func, gflag=True):
        args = ", ".join(self.sig.parameters.keys())
        name = func.__name__
        test_name = f'test_{name}'

        # explicitly import the function to be tested at the runtime location
        # gloabal statement ensures the test function is in the global namespace
        # at runtime
        code = textwrap.dedent(
            f'''
            from {func.__module__} import {name}

            global {name}
            def {test_name}({args}, output):
                assert {name}({args}) == output

            ''')

        # TODO: the code above obfuscates the pytest error diagnostics. can you
        # find a way to still get diagnostic messages??

        # print(code)
        # print('running {test_name}')
        # print('{name} in globals?', '{name}' in globals())
        # print('{name} in locals?', '{name}' in locals())
        return test_name, code
