
"""
Tools to help building unit tests

To generate a bunch of tests with various call signatures of the function
`iter_lines`, use
>>> from recipes.testing import Expect, mock
>>> test_iter_lines = Expect(iter_lines)(
...     {mock.iter_lines(filename, 5):                      srange(5),
...      mock.iter_lines(filename, 5, 10):                  srange(5, 10),
...      mock.iter_lines(filename, 3, mode='rb'):           brange(3),
...      mock.iter_lines(filename, 3, mode='rb', strip=''): bnrange(3)},
...     transform=list
... )

This will generate the same tests as the following code block, but is obviously
much neater
>>> @pytest.mark.parametrize(
...     'section, mode, strip, result',
...     [((5, ),  'r', None,  srange(5)),
...      ((3, 8), 'r', None,  srange(3, 8)),
...       ((3,),  'rb', None, brange(3)),
...       ((3,),  'rb', '',   bnrange(3)) ]
... )
... def test_iter_lines(filename, section, mode, strip, result):
...     print(filename)
...     assert list(iter_lines(filename, *section, mode=mode, strip=strip)) == result

"""

from recipes.lists import lists
import types
import inspect
import textwrap
from collections import defaultdict
from recipes.pprint import caller

import pytest

from recipes.iter import cofilter, negate

# FIXME: get this to work inside a class!!

# TODO: expected decorator

# @expected(
#     (CAL/'SHA_20200822.0005.fits', shocBiasHDU,
#      CAL/'SHA_20200801.0001.fits', shocFlatHDU,
#      EX1/'SHA_20200731.0022.fits', shocNewHDU)
# )
# def hdu_type(filename):
#     return _BaseHDU.readfrom(filename).__class__


def to_tuple(obj):
    if isinstance(obj, tuple):
        return obj
    return obj,


def get_hashable_args(*args, **kws):
    return args, tuple(kws.items())


def echo(args):
    return args


def isfixture(obj):
    return (isinstance(obj, types.FunctionType) and
            hasattr(obj, '_pytestfixturefunction'))


class WrapArgs:
    def __init__(self, *args, **kws):
        self.args, self.kws = get_hashable_args(*args, **kws)

    def __iter__(self):
        return iter((self.args, self.kws))


class Mock:
    def __getattr__(self, _):
        return WrapArgs

    def __call__(self, *args, **kws):
        return


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


# @expected(patterns)
# def test_brace_expand(pattern, result):
#     assert bash.brace_expand(pattern) == result


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
    Testing helper for checking expected return values for functions/ methods.
    Allows one to build simple paramertized tests of complex function without
    needing to explicitly type an exhaustive combination of exact function
    parameters (of which there may be many)

    For example, to test that the function `hms` returns the expected
    values, do the following:
    >>> from recipes.testing import Expect, mock
    >>> test_hms = Expect(hms)(
    ...     {mock.hms(1e4):                             '02h46m40.0s',
    ...      mock.hms(1.333121112e2, 5):                '00h02m13.31211s',
    ...      mock.hms(1.333121112e2, 5, ':'):           '00:02:13.31211',
    ...      mock.hms(1.333121112e2, 5, short=False):   '00h02m13.31211s',
    ...      mock.hms(1.333121112e2, 'm0',
    ...               short=False, unicode=True):       '00ʰ02ᵐ',
    ...      mock.hms(119.95, 's0'):                    '00h02m00s',
    ...      mock.hms(1000, 'm0', sep=':'):             '00:17',
    ...      }
    ... )

    This will automatically construct a test function: 'test_dicimal' which has
    the same signature as the function `decimal`, with a single parameter
    `results` added. The sequence of input output pairs passed to the `expects`
    method is used to parametrize the test, so that pytest will include all
    cases in your test run. Assigning the output of the `expects` method above
    to a variable name starting with 'test_' is important for pytest test
    discovery to work correctly.
    """

    def __init__(self, func, test_name=None):
        #
        self.func = func
        # crude test for whether this function is defined in a class scope
        self.is_method = (func.__name__ != func.__qualname__)
        # get test signature
        self.sig = inspect.signature(self.func)

        # mock
        setattr(self, func.__name__, get_hashable_args)

        # optional name
        self.test_name = test_name or f'test_{func.__name__}'
        self.test_code = None

    def __call__(self, items, *args, **kws):
        return self.expects(items, *args, **kws)

    def expects(self, items, *args, transform=echo, **kws):
        """
        Main worker method to create the test if necessary and parameterize it

        Parameters
        ----------
        items : [type]
            [description]

        Returns
        -------
        [type]
            [description]
        """
        if isinstance(items, dict):
            items = items.items()

        # create the test
        test = self.make_test(transform)

        # parse the arguments
        if self.func.__name__.startswith('test_'):
            # already have the test function defined
            argspecs = self.get_args(items)
        else:
            # test created test function signature has 1 extra parameter
            argspecs, answers = zip(*items)
            argspecs = self.get_args(argspecs)
            argspecs['result'] = answers

        names = argspecs.keys()
        values = zip(*argspecs.values())
        *values, names = cofilter(negate(isfixture), *values, names)
        names, values = list(names), lists(values)
        print(names, values)
        # from IPython import embed
        # embed(header="Embedded interpreter at 'testing.py':187")
        return pytest.mark.parametrize(list(names), lists(values),
                                       *args, **kws)(test)

    def bind(self, *args, **kws):
        ba = self.sig.bind(*args, **kws)
        ba.apply_defaults()
        return ba

    def get_args(self, items):
        # loop through the input argument list (items) and create the full
        # parameter spec for the function by binding each call pattern
        # to the function signature. Return a dict keyed on parameter names
        # containing lists of parameter values for each call.
        values = defaultdict(list)
        for spec in items:
            if not isinstance(spec, WrapArgs):
                # simple construction without use of mock function. No keyword
                # values in arg spec
                spec = WrapArgs(*to_tuple(spec))

            # call signature emulation via mock handled here
            args, kws = spec
            args = (None,) * self.is_method + args
            args = self.bind(*args, **dict(kws))

            for name, val in tuple(args.arguments.items())[self.is_method:]:
                values[name].append(val)
        # from IPython import embed
        # embed(header="Embedded interpreter at 'testing.py':212")
        return values

    def make_test(self, transform=echo):

        if self.func.__name__.startswith('test_'):
            # already have the test function defined
            return self.func

        # create the test
        self.test_code = self.get_test_code(transform)

        locals_ = {}
        exec(self.test_code, None, locals_)
        return locals_[self.test_name]

    def get_test_code(self, transform):
        name = self.func.__name__
        test_name = self.test_name or f'test_{name}'

        # construct the signature for the function call inside the test. We have
        # to use 'param=param' syntax for the keyword only arguments. Using
        # pprint.caller.signature will ensure the variadic-positional and
        # -keyword arguments get their stars, that the keyword-only
        # parameters are formated like 'param=param', and that the pep570
        # markers are excluded in order to emulate a function call syntax
        KWO = inspect.Parameter.KEYWORD_ONLY
        sig = inspect.Signature(
            [par.replace(default=par.empty if par.kind != KWO else name)
             for name, par in self.sig.parameters.items()])
        call_sig = caller.signature(
            sig, value_formatter=str, pep570_marks=False)

        # signature for test function itself. Just string all the parameter
        # names together
        result_name = 'result'
        args = ', '.join(list(self.sig.parameters.keys()) + [result_name])

        # explicitly import the function to be tested at the runtime location
        # gloabal statement ensures the test function is in the global namespace
        # at runtime
        code = textwrap.dedent(
            f'''
            from {self.func.__module__} import {name}

            global {name}
            def {test_name}({args}):
                assert {transform.__name__}({name}{call_sig}) == {result_name}

            ''')

        # TODO: the code above obfuscates the pytest error diagnostics. can you
        # find a way to still get diagnostic messages??

        print(code)
        # print('running {test_name}')
        # print('{name} in globals?', '{name}' in globals())
        # print('{name} in locals?', '{name}' in locals())
        return code
