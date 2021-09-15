# Flexibly parametrize functional tests

"""
Tools to help building parametrized unit tests

Examples
--------
To generate a bunch of tests with various call signatures of the function
`iter_lines`, use
>>> from recipes.testing import Expected, mock
>>> test_iter_lines = Expected(iter_lines)(
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

# std
import types
import difflib
import itertools as itt
from contextlib import nullcontext
from collections import defaultdict
from inspect import signature, Signature, Parameter, _ParameterKind

# third-party
import pytest

# local
import motley

# relative
from ...logging import LoggingMixin
from . import pprint as pp
from .lists import lists
from .iter import cofilter, negate
from .functionals import echo0 as echo


POS, PKW, VAR, KWO, VKW = _ParameterKind


def to_tuple(obj):
    if isinstance(obj, tuple):
        return obj
    return (obj, )


def get_hashable_args(*args, **kws):
    return args, tuple(kws.items())


def isfixture(obj):
    return (isinstance(obj, types.FunctionType) and
            hasattr(obj, '_pytestfixturefunction'))


def show_diff(actual, expected):
    """
    Diff helper function. Returns a string containing the unified diff of two
    multiline strings.
    """

    return ''.join(difflib.unified_diff(actual.splitlines(True),
                                        expected.splitlines(True)))


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

# test_hms = Expected(hms).expects(
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


class Warns:
    def __init__(self, warning=UserWarning):
        self.warning = warning

# @pytest.mark.parametrize('s', ['(', 'also_open((((((', '((())'])
# def test_brackets_must_close_raises(s):
#     with pytest.raises(ValueError):
#         match_brackets(s, must_close=True)


class ECHO:
    """Echo sentinal"""


class PASS:
    """
    Signify that any result from a test is permissable, as long as it passes
    without exception.
    """


class expected:
    """
    Examples
    --------
    >>> @expected({
    ...      # test input (cases)        # expected result
    ...      CAL/'SHA_20200822.0005.fits': shocBiasHDU,
    ...      CAL/'SHA_20200801.0001.fits': shocFlatHDU,
    ...      EX1/'SHA_20200731.0022.fits': shocNewHDU
    ... })
    ... def hdu_type(filename):
    ...     return _BaseHDU.readfrom(filename).__class__
    """

    def __init__(self, cases, *args, **kws):
        self.cases = cases
        self.args = args
        self.kws = kws
        # self.parent = None

    def __call__(self, func):
        # func.owner = self.parent
        return Expected(func, **self.kws)(self.cases, *self.args)


PKW = Parameter.POSITIONAL_OR_KEYWORD
KWO = Parameter.KEYWORD_ONLY


def get_transforms(main, left, right):
    if main is not None:
        assert callable(main)
        left = right = main

    assert callable(left) and callable(right)
    return left, right


# TODO:
# class Case

class Expected(LoggingMixin):
    """
    Testing helper for checking expected return values for functions/ methods.
    Allows one to build simple paramertized tests of complex function without
    needing to explicitly type an exhaustive combination of exact function
    parameters (of which there may be many)

    For example, to test that the function `hms` returns the expected
    values, do the following:
    >>> from recipes.testing import Expected, mock
    >>> test_hms = Expected(hms)(
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

    # result_name = 'expected'

    def __init__(self, func,
                 left_transform=echo, right_transform=echo, transform=None,
                 **kws):
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
        self.vkw = self.var = None
        self.pnames = params = ()
        if self.sig.parameters:
            self.pnames, params = zip(*self.sig.parameters.items())
        self.pkinds = kinds = [p.kind for p in params]
        for k, v in dict(vkw=VKW, var=VAR).items():
            if v in kinds:
                setattr(self, k, self.pnames[kinds.index(v)])

        # mock
        # setattr(self, name, get_hashable_args)
        # results transform
        # self.transform = transform

        self.left_transform, self.right_transform = \
            get_transforms(transform, left_transform, right_transform)

    def __call__(self, cases, *args,
                 left_transform=None, right_transform=None, transform=None,
                 **kws):
        """
        Main worker method to create the test if necessary and parameterize it

        Parameters
        ----------
        cases : [type]
            [description]

        Returns
        -------
        [type]
            [description]
        """

        left_transform, right_transform = get_transforms(
            transform,
            left_transform or self.left_transform,
            right_transform or self.right_transform
        )

        if isinstance(cases, dict):
            cases = cases.items()
        elif isinstance(cases, (list, tuple)):
            # if passing list, signify that all we want is for the tests to
            # complete. return values will not be checked
            cases = zip(cases, itt.repeat(PASS))

        # create test / parse the arguments
        if self.is_test:
            # already have the test function defined
            test = self.func
        else:
            # create the test
            test = self.make_test(left_transform, right_transform)

        argspecs = self.get_args(cases)
        names = argspecs.keys()
        values = zip(*argspecs.values())
        *values, names = cofilter(negate(isfixture), *values, names)
        names, values = list(names), lists(values)

        # if logger.getEffectiveLevel() == logging.DEBUG:
        #     logger.debug('parametrizing {:s}', pp.caller(test))
        #     logger.debug(f'{names=}')  # , {values=}')

        # return ParametrizedTestHelper(test, names, values, *args, **kws)
        # # NOT WORKING:
        # PytestCollectionWarning: cannot collect because it is not a function

        return pytest.mark.parametrize(names, values, *args, **kws)(test)

    def run(self, items, *args, transform=echo, **kws):
        # TODO: remove this. you can just pass a list to the decorator
        """
        For simple tests, merely check if the function succeeds.

        Parameters
        ----------
        items : iterable
            Sequence of arguments to pass to the function

        Examples
        --------
        >>> test_init = Expected(TimeSeries).run(
        ...     [ mock.TimeSeries(y),
        ...       mock.TimeSeries(y2),
        ...       mock.TimeSeries(t, y),
        ...       mock.TimeSeries(t, y, e),
        ...       mock.TimeSeries(t, ym, e) ]
        ...     )
        """
        items = zip(items, itt.repeat(PASS))
        return self(items, *args, left_transform=transform, **kws)

    def bind(self, *args, **kws):
        if self.is_method:
            args = (None, *args)

        bound = self.sig.bind(*args, **kws)
        bound.apply_defaults()
        params = bound.arguments

        if self.is_method:
            params.pop('self')

        return params

    def get_args(self, items):
        # loop through the input argument list (items) and create the full
        # parameter spec for the function by binding each call pattern
        # to the function signature. Return a dict keyed on parameter names
        # containing lists of parameter values for each call.

        values = defaultdict(list)
        for spec in items:
            # call signature emulation via mock handled here
            spec, result = spec

            if not isinstance(spec, WrapArgs):
                # simple construction without use of mock function.
                # ==> No keyword values in arg spec
                spec = WrapArgs(*to_tuple(spec))

            args, kws = spec
            kws = dict(kws)
            bound = None
            if result is ECHO:
                bound = self.bind(*args, **{**self.kws, **kws})
                result = list(bound.values())[self.is_method]

            if self.is_test:
                kws['expected'] = result
            else:
                # signature of created test function has 1 extra parameter
                values['expected'].append(result)

            if not bound:
                try:
                    bound = self.bind(*args, **{**self.kws, **kws})
                except TypeError as err:
                    msg = 'too many positional arguments'
                    if msg in str(err) and self.is_test:
                        err = TypeError(
                            f'{msg.title()}: Perhaps you accidentally prefixed'
                            f' a decorated function with "test_".'
                        )
                    raise err from None

            for name, val in tuple(bound.items()):
                values[name].append(val)

        return values

    def make_test(self, left_transform, right_transform):

        def test(*args, **kws):
            #
            self.logger.debug('test received: {:s}, {:s}', args, kws)

            expected = kws.pop('expected')
            vkw = kws.pop(self.vkw, {})
            kws = {**kws, **vkw}
            var = kws.pop(self.var, ())
            if var:
                args = (*(kws.pop(name) for name in
                          self.pnames[:self.pkinds.index(VAR)]),
                        var)

            self.logger.debug('passing to {:s}: {:s}; {:s}',
                         self.func.__name__, args, kws)

            ctx = nullcontext()
            if isinstance(expected, Throws):
                ctx = pytest.raises(expected.error)
            elif isinstance(expected, Warns):
                ctx = pytest.warns(expected.warning)

            with ctx:
                answer = left_transform(self.func(*args, **kws))

            if (expected is PASS) or not isinstance(ctx, nullcontext):
                return

            expected = right_transform(expected)
            # NOTE: explicitly assigning answer here so that pytest
            # introspection of locals in this scope works when producing the
            # failure report
            if answer != expected:

                message = '\n'.join((
                    'Result from function '
                    f'{motley.green(repr(self.func.__name__))}'
                    ' is not equal to expected answer!',
                    f'RESULT:\n{answer}',
                    f'EXPECTED:\n{expected}'
                ))
                if isinstance(answer, str) and isinstance(expected, str):
                    message += f'\nDIFF\n{show_diff(answer, expected)}'

                raise AssertionError(message)

        # Override signature to add `expected` parameter
        # Add `expected` parameter after variadic keyword arguments
        params = [par.replace(default=par.empty, kind=PKW)
                  for name, par in self.sig.parameters.items()]
        params.append(Parameter('expected', KWO))
        test.__signature__ = Signature(params)

        self.logger.debug('Created test for function\n{:s} with signature:\n{:s}',
                     pp.caller(self.func), test.__signature__)

        return test


# class TestDescriptorHelper:

class ParametrizedTestHelper(LoggingMixin):  # ParametrizedTest:
    # set the 'test_xxx' name on classes for automatically constructed tests
    # inside class scope

    def __init__(self, test, names, values, *args, **kws):
        self.test = test
        self.logger.debug('parametrizing {:s}', pp.caller(test))
        # self.logger.debug('signature: {:s}', pp.caller(test))
        # self.logger.debug(f'{names=}')  # , {values=}')
        self.runner = pytest.mark.parametrize(
            list(names), lists(values), *args, **kws
        )(test)

    def __call__(self, *args, **kws):
        return self.runner(*args, **kws)

    def __set_name__(self, kls, name):
        self.logger.debug('Binding {:s} onto class {:s} with name {!r:}',
                     self.test, kls, name)
        if not name.startswith('test'):
            self.logger.debug(
                "renaming test function: {!r:} -> 'test_{:s}'", name, name)
            name = f'test_{name}'

        setattr(kls, name, self.runner)
