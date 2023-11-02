
# std
import re
import random
from inspect import inspect

# third-party
from pytest_cases import parametrize

# local
from recipes import pprint as pp
from recipes.string import replace_suffix
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
def test_caller_basic(fun):
    # check if we are faithfully reproducing the signature
    # builtin signature rep prints trailing PEP570 / marker which is meaningless
    sig = replace_suffix(fun.sig, ', /)', ')')
    assert pp.caller(fun.fun).endswith(sig)


@parametrize(
    'fun, spec',
    ((fun, spec) for fun in cases for spec in generate_params(fun.fun)),
    idgen='{fun.fun.__name__}{spec}'
)
def test_caller_defaults(fun, spec):
    # check if defaults are represented / dropped
    args, kws = spec
    d = pp.caller(fun.fun, args, kws, show_defaults=True)
    xd = r = pp.caller(fun.fun, args, kws, show_defaults=False)
    for i, arg in enumerate(REGEX_PARAMS.finditer(fun.sig)):
        if (arg['default']
            and (len(args) <= i or not args[i])
                and arg['name'] not in kws):

            # value not specified
            par_val = arg[1]
            assert par_val in d
            assert par_val not in xd


# extra = []  # [id, float, callable, tidy]
# for i, fun in enumerate((functions + extra)):  #
#     # check if we are faithfully reproducing the signature
#     # print('Signature')
#     # print(pp.caller(fun))
#     # print('--------')

#     for spec in avg(fun):
#         # print('\nArgspec:', *spec)

#         test_pprint_caller(fun, *spec, show_defaults=False)

#         if has_defaults(inspect.signature(fun).parameters):
#             test_pprint_caller(fun, *spec, show_defaults=True)

#     print('=' * 80)

    #     break
    # # test_show_func(fun)

    # # for name, par in inspect.signature(fun).parameters.items():
    # #     print(name, par.kind)

    # # print(inspect.getfile(fun))
    # # mod = inspect.getmodule(fun)
    # # print(get_module_name(mod.__file__))

    # print('=' * 88)
    # # break

    # if i == 4:
    #     break
