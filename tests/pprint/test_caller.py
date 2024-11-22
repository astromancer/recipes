
# std
import re
import random
import inspect
import itertools as itt

# third-party
from loguru import logger
from pytest_cases import parametrize

# local
from recipes import pprint as pp
from recipes.functionals.factory import FunctionFactory, ParamValueGenerator


# pylint: disable-all

# ---------------------------------------------------------------------------- #
# ensure repeatability
random.seed(123)

REGEX_PARAMS = re.compile(r'((?P<name>\w+)(?:=(?P<default>.+?))?),')


# ---------------------------------------------------------------------------- #

def random_string(n):
    return ''.join(chr(random.randint(97, 122)) for _ in range(n))


def gen_random_string(n):
    while True:
        yield random_string(n)


# ---------------------------------------------------------------------------- #
# Helper class
class FuncTestingWrapper:
    def __init__(self, fun):
        self.fun = fun
        self.sig = str(inspect.signature(fun))
        self.code = fun.__source__


# ---------------------------------------------------------------------------- #
# Create Functions
POS, PKW, VAR, KWO, VKW = inspect._ParameterKind
SPEC = {POS: 1,
        PKW: 1,
        VAR: 1,
        KWO: 1,
        VKW: 1}


factory = FunctionFactory('abc', range(5))(SPEC)
cases = [*map(FuncTestingWrapper, factory)]
generate_params = ParamValueGenerator(arg_pool=[1, 2, 3, 4, 5],
                                      var_pool=gen_random_string(3),
                                      kws_pool=[{'λ': 'r'}, {'x': 'v'}])


# @fixture(scope='session')
# @parametrize(fun=factory)
# def fun(fun):
#     return FuncHelper(fun)


# ---------------------------------------------------------------------------- #
# def test_test(fun):
#     pass

# def inner(a, b, c):
#     pass

# p0 = ftl.partial(inner, a=1)
# p1 = ftl.partial(p0, b=2)
# p1, p0


@parametrize(fun=cases, idgen='{fun.fun.__name__}')
def test_signature(fun):
    # check if we are faithfully reproducing the signature
    s = pp.caller(fun.fun)
    assert s.endswith(str(fun.sig))
    logger.debug('')
    logger.debug('Builtin signature reproduced:           {}.', s)
    assert s in fun.code
    logger.debug('Signature matches definition in source: {}.', s)


@parametrize(
    'fun, spec',
    ((fun, spec) for fun in cases for spec in generate_params(fun.fun)),
    idgen='{fun.fun.__name__}{spec}'
)
def test_caller_defaults(fun, spec):
    # check if defaults are represented / dropped
    args, kws = spec
    # s = pp.caller(fun.fun)

    # logger.debug(, fun.fun, fun.code)

    results = {}
    msg = ('Test case: {.__name__}:\n'
           'Definition:\n{}\n'
           'Invocations: args = {}; kws = {}.\n')
    for names, defaults in itt.product([True, None], [True, False]):
        results[(names, defaults)] = s = \
            pp.caller(fun.fun, args, kws,
                      param_names=names,
                      show_defaults=defaults)
        #
        msg += f'{names = !s: <5}; {defaults = !s: <5}: {s}\n'.replace('{', '{{').replace('}', '}}')

    #
    logger.debug(msg, fun.fun, fun.code, args, kws)

    # xd = pp.caller(fun.fun, args, kws, show_defaults=False)
    # xn = pp.caller(fun.fun, args, kws, param_names=None)

    # TODO: annotatons on / off
    #       names on /off

    # for i, arg in enumerate(REGEX_PARAMS.finditer(fun.sig)):
    #     if (arg['default']
    #         and (len(args) <= i or not args[i])
    #             and arg['name'] not in kws):

    #         # value not specified
    #         par_val = arg[1]
    #         assert par_val in d
    #         assert par_val not in xd
