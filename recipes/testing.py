
"""
Tools to help building parametrized unit tests

Example
-------
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
    def __init__(self, kind=Exception):
        self.kind = kind

# @pytest.mark.parametrize('s', ['(', 'also_open((((((', '((())'])
# def test_brackets_must_close_raises(s):
#     with pytest.raises(ValueError):
#         match_brackets(s, must_close=True)


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
        self.sig = inspect.signature(self.func)

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
            # TODO Tester(self.func, transform)
            # created test function signature has 1 extra parameter
            argspecs, answers = zip(*items)
            argspecs = self.get_args(argspecs)
            argspecs[self.result_name] = answers

        names = argspecs.keys()
        values = zip(*argspecs.values())
        *values, names = cofilter(negate(isfixture), *values, names)
        # names, values = list(names), lists(values)
        # logger.debug(f'{names=}, {values}')
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
                # simple construction without use of mock function. No keyword
                # values in arg spec
                spec = WrapArgs(*to_tuple(spec))

            args, kws = spec
            if self.is_test:
                args += (result, )
            args = (None,) * self.is_method + args
            args = self.bind(*args, **dict(kws))
            for name, val in tuple(args.arguments.items())[self.is_method:]:
                values[name].append(val)

        return values

    def make_test(self, transform=echo):

        # create the test
        self.test_code = self.get_test_code(transform.__name__)

        locals_ = {}
        exec(self.test_code, None, locals_)
        return locals_[self.test_name]

    def get_test_code(self, transform):
        name = self.func.__name__
        test_name = self.test_name or f'test_{name}'

        # signature for test function itself. Just string all the parameter
        # names together
        
        args = ', '.join([*self.sig.parameters.keys(), *[self.result_name]])

        # construct the signature for the function call inside the test. We have
        # to use 'param=param' syntax for the keyword only arguments. Using
        # pprint.caller.signature will ensure the variadic-positional and
        # -keyword arguments get their stars, that the keyword-only
        # parameters are formated like 'param=param', and that the pep570
        # markers are excluded in order to emulate a function call syntax
        KWO = inspect.Parameter.KEYWORD_ONLY

        sig = inspect.Signature(
            [par.replace(default=(name if par.kind == KWO else
                                  self.kws.get(name, par.empty)))
             for name, par in self.sig.parameters.items()]
        )
        # sig.bind_partial(**self.kws)

        call_sign = caller.signature(sig, value_formatter=str,
                                         pep570_marks=False)
        

        # explicitly import the function to be tested at the runtime location
        # gloabal statement ensures the test function is in the global namespace
        # at runtime
        code = textwrap.dedent(
            f'''
            from {self.func.__module__} import {name}

            global {name}
            def {test_name}({args}):
                if isinstance(expected, Throws):
                    with pytest.raises(expected.error):
                        return {transform}({name}{call_sign})
                      
                assert {transform}({name}{call_sign}) == {self.result_name}
            ''')

        # if

        # TODO: the code above obfuscates the pytest error diagnostics. can you
        # find a way to still get diagnostic messages??

        logger.debug(f'code:\n{code}')
        # print('running {test_name}')
        # print('{name} in globals?', '{name}' in globals())
        # print('{name} in locals?', '{name}' in locals())
        return code

class Tester():
    result_name = 'expected'
    
    def __init__(self, fun, transform):
        self.fun = fun
        self.transform = transform
    
    def test(self, answer, args, kws):
    
        if isinstance(expected, Throws):
            with pytest.raises(expected.error):
                return self.transform(fun(*args, **kws))
                    
        assert self.fun(*args, **kws) == answer
        

# class ExpectFailure:
#     def __init__(self, error):
#         self._TestCaseNonHashableDefaults
