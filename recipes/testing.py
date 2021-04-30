
"""
Tools to help building parametrized unit tests

Examples
--------
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

This will generate the same tests as the following code block, but is arguably
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

from .functionals import echo
from recipes.lists import lists
import types
from inspect import signature, Signature, Parameter, _ParameterKind
import textwrap
from collections import defaultdict
from recipes import op, pprint as pp
# import unittest as ut

import pytest

from recipes.iter import cofilter, negate
from recipes.logging import get_module_logger

import logging

# module level logger
logging.basicConfig()
logger = get_module_logger()
logger.setLevel(logging.DEBUG)


# FIXME: get this to work inside a class!!

# TODO: expected decorator

# @expected(
#     (CAL/'SHA_20200822.0005.fits', shocBiasHDU,
#      CAL/'SHA_20200801.0001.fits', shocFlatHDU,
#      EX1/'SHA_20200731.0022.fits', shocNewHDU)
# )
# def hdu_type(filename):
#     return _BaseHDU.readfrom(filename).__class__


POS, PKW, VAR, KWO, VKW = _ParameterKind


def to_tuple(obj):
    if isinstance(obj, tuple):
        return obj
    return obj,


def get_hashable_args(*args, **kws):
    return args, tuple(kws.items())


def isfixture(obj):
    return (isinstance(obj, types.FunctionType) and
            hasattr(obj, '_pytestfixturefunction'))


class WrapArgs:
    def __init__(self, *args, **kws):
        self.args, self.kws = get_hashable_args(*args, **kws)

    def __iter__(self):
        return iter((self.args, self.kws))

    def __str__(self) -> str:
        return str((self.args, dict(zip(*self.kws))))


class Mock:
    def __getattr__(self, _):
        return WrapArgs

    def __call__(self, *args, **kws):
        return WrapArgs(*args, **kws)


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

class Throws:
    def __init__(self, error=Exception):
        self.error = error

# @pytest.mark.parametrize('s', ['(', 'also_open((((((', '((())'])
# def test_brackets_must_close_raises(s):
#     with pytest.raises(ValueError):
#         match_brackets(s, must_close=True)


class expected:
    """
    Examples
    --------
    >>> @expected({
    ...     # test input                   # expected result
    ...      CAL/'SHA_20200822.0005.fits': shocBiasHDU,
    ...      CAL/'SHA_20200801.0001.fits': shocFlatHDU,
    ...      EX1/'SHA_20200731.0022.fits': shocNewHDU
    ... })
    ... def hdu_type(filename):
    ...     return _BaseHDU.readfrom(filename).__class__
    """

    def __init__(self, items, *args, **kws):
        self.items = items
        self.args = args
        self.kws = kws

    def __call__(self, func):
        return Expect(func)(self.items, *self.args, **self.kws)


PKW = Parameter.POSITIONAL_OR_KEYWORD
KWO = Parameter.KEYWORD_ONLY


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

    result_name = 'expected'

    def __init__(self, func, **kws):
        #
        self.func = func
        self.kws = kws
        name = func.__name__
        # whether it's intended to be a test already
        self.is_test = name.startswith('test_')
        # crude test for whether this function is defined in a class scope
        self.is_method = (name != func.__qualname__)
        # get func signature
        self.sig = signature(self.func)

        # mock
        setattr(self, name, get_hashable_args)

        # optional name
        self.test_name = f'test_{name}'
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

        # create test / parse the arguments
        if self.is_test:
            # already have the test function defined
            test = self.func
            argspecs = self.get_args(items)
        else:
            # create the test
            test = self.make_test(transform)
            # created test function signature has 1 extra parameter
            argspecs, answers = zip(*items)
            argspecs = self.get_args(argspecs)
            argspecs[self.result_name] = answers

        names = argspecs.keys()
        values = zip(*argspecs.values())
        *values, names = cofilter(negate(isfixture), *values, names)
        names, values = list(names), lists(values)
        logger.debug(f'signature: {pp.caller(test)}')
        logger.debug(f'{names=}, {values=}')

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
            # call signature emulation via mock handled here
            if self.is_test:
                spec, result = spec

            if not isinstance(spec, WrapArgs):
                # simple construction without use of mock function.
                # ==> No keyword values in arg spec
                spec = WrapArgs(*to_tuple(spec))

            args, kws = spec
            if self.is_test:
                args += (result, )

            args = self.bind(*args, **dict(kws))
            for name, val in tuple(args.arguments.items()):
                values[name].append(val)

        return values

    def make_test(self, transform=echo):

        def test(*args, expected, **kws):
            if isinstance(expected, Throws):
                with pytest.raises(expected.error):
                    self.func(*args, **kws)
            else:
                answer = transform(self.func(*args, **kws))
                # NOTE: explicitly assigning answer here so that pytest
                # introspection of locals in this scope works when producing the
                # failure report
                assert answer == expected

        # Override signature
        params = [par.replace(default=(name if par.kind == KWO else
                                       self.kws.get(name, par.empty)))
                  for name, par in self.sig.parameters.items()]
        kinds = [p.kind for p in self.sig.parameters.values()]
        i = op.index(kinds, VKW, default=len(kinds))

        test.__signature__ = Signature(
            [*params[:i], Parameter(self.result_name, KWO), *params[i:]]
        )

        return test


# class ExpectFailure:
#     def __init__(self, error):
#         self._TestCaseNonHashableDefaults
