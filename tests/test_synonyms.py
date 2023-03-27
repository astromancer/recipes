# std
import inspect
from collections import deque

# third-party
import pytest
from loguru import logger

# local
from recipes import api, dicts
from recipes.pprint import callers
from recipes.function_factory import FunctionFactory


# ---------------------------------------------------------------------------- #
logger.enable('recipes.api.synonyms')

# ---------------------------------------------------------------------------- #
API_ALIASES = {'a': 'abra',
               'c': 'cada',
               'b': 'bra'}


PKIND = POS, PKW, VAR, KWO, VKW = list(inspect._ParameterKind)
# ---------------------------------------------------------------------------- #


class SynTestFactory(FunctionFactory):
    def make(self, name, params, class_name=None, body=None):
        kws = {}
        for p in params:
            name = p.name
            if name in API_ALIASES:
                kws[API_ALIASES[name]] = None
            if p.name == 'kws':
                kws = {'abra': None,
                       'cadab': None,
                       'bra': None}

        f = super().make(name, params, class_name, body)
        return f, ((), kws)

    @staticmethod
    def get_code(name, params, class_name=None, body=''):
        vkw = var = False
        unused = set('abc')
        body = body or ''  # 'print("LOCALS", locals())\n'
        for p in params:
            if p.name in 'abc':
                body += f'assert {p.name} is None, f"{{{p.name}=}}"\n'
                unused.remove(p.name)
            elif p.kind == VKW:
                vkw = True
            elif p.kind == VAR:
                var = True

        if vkw:
            for u in unused:
                body += f'assert kws["{u}"] == {ord(u) - 97}\n'

        if var:
            body += f'assert args == ()\n'

        return FunctionFactory.get_code(name, params, class_name, body)


# class Foo:

#     @classmethod
#     @api.synonyms({
#         'convert':                  'converters',
#         'split_nested(_types?)?':   'split_nested_types'
#     })
#     def from_dict(cls, data, converters=(), ignore_keys=(), convert_keys=(),
#                   order='r', col_sort=None, **kws):
#         assert 'convert' not in kws
#         return cls(data, **kws)

#     def __init__(self, *args, **kws):
#         self.args, self.kws = args, kws


POS, PKW, VAR, KWO, VKW = inspect._ParameterKind
SIG_SPEC = {POS: 1,
            PKW: 1,
            # VAR: 1,
            KWO: 1,
            VKW: 1}

factory = SynTestFactory('abc', [None], function_body='')(SIG_SPEC)
syn = api.synonyms(dicts.invert(API_ALIASES))
# {val: key for key, val in API_ALIASES.items()}


@pytest.mark.parametrize(
    'fun, spec', factory,
    # idgen='{fun.fun.__name__}{spec}'
)
def test_subs(fun, spec):
    args, kws = spec
    decorated = syn(fun)
    decorated(*args, **kws)


def test_kws():

    class Case:
        @api.synonyms({'convert': 'converters'})
        def from_dict(self, data, converters=(), **kws):
            assert 'convert' not in kws

    case = Case()
    case.from_dict(None, convert=True)
    with pytest.raises(TypeError):
        case.from_dict(None, None, convert=True)


def test_kws_classmethod():

    class Case:
        @classmethod
        @api.synonyms({'convert': 'converters'})
        def from_dict(cls, data, converters=(), **kws):
            assert 'convert' not in kws

    Case.from_dict(None, convert=True)
    with pytest.raises(TypeError):
        Case.from_dict(None, None, convert=True)

# def test_kws():

#     class Case:
#         @api.synonyms({
#             'convert':                  'converters',
#             # 'split_nested(_types?)?':   'split_nested_types'
#         })
#         def from_dict(self, data, converters=(), ignore_keys=(), convert_keys=(),
#                     order='r', col_sort=None, **kws):
#             print(kws)
#             assert 'convert' not in kws
#             # return cls(data, **kws)


#     # print(Case.from_dict.__wrapper__.__self__.resolve((), {'convert': ''}))
#     Case().from_dict(None, convert=True)


# for fun, spec in factory:
#     print('FUN: ', caller(fun))
#     print('PARAMS:', spec)
# #     # Last item is the full set of parameters for function signature, that's the
# #     # one we want for the test here
#     # sig = inspect.signature(fun)
#     # params = sig.parameters
#     # *_, spec = gen_pars(fun)
# #     print(spec)
#     test_subs(fun, spec)
#     print('*' * 88, '\n')


# class TestSubs:

#     @pytest.mark.parametrize(
#         'fun, spec',
#         ((fun, deque(gen_pars(fun)).pop()) for fun in factory),
#         # idgen='{fun.fun.__name__}{spec}'
#     )
#     def test_subs(self, fun, spec):
#         args, kws = spec
#         print(args, kws)
#         self.syn(fun)(*args, **kws)


# # def test_classmethod():
# Foo.from_dict(None, convert='fark')
