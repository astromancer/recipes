
from pytest_cases import fixture, parametrize, get_all_cases
import re
# from pytest_steps import test_steps
import more_itertools as mit
from collections import defaultdict
from inspect import Parameter

from recipes import pprint as pp
from recipes.string import replace_suffix
from recipes.logging import get_module_logger
import inspect
import logging


import itertools as itt
import textwrap as txw
import random

import pytest

# ensure repeatability
random.seed(123)

# module level logger
logging.basicConfig()
logger = get_module_logger()
logger.setLevel(logging.INFO)


PKIND = POS, PKW, VAR, KWO, VKW = list(inspect._ParameterKind)

# pylint: disable-all
# Make a bunch of function definitions for testing
#
# 'a', 'a=0'
# '/',
# 'b', 'c=2'
# '*args', '*'
# 'd=3'
# '**kws'


# TODO: generate function from choices from below


# argspec = {POS: (name_pool, default_pool),
#            PKW: (name_pool, default_pool),
#            VAR: (itt.repeat('*args'), itt.repeat(Parameter.empty)),
#            KWO: (name_pool, default_pool),
#            VKW: (itt.repeat('**kws'), itt.repeat(Parameter.empty))}

# # varspec = {VAR: (itt.repeat('*args'), itt.repeat(Parameter.empty)),
#            VKW: (itt.repeat('**kws'), itt.repeat(Parameter.empty))}


def random_string(n):
    return ''.join((chr(random.randint(97, 122)) for i in range(n)))


def gen_random_string(n):
    while True:
        yield random_string(n)


def has_default(par):
    return par.default is not par.empty


def is_required(par):
    return not (is_var(par) or has_default(par))


def is_var(par):
    return par.kind in (VAR, VKW)


def _has(params, func):
    for name, par in params.items():
        if name == 'self':
            continue
        if func(par):
            return True
    return False


def has_defaults(params):
    return _has(params, has_default)


def has_required(params):
    return _has(params, is_required)


def has_var(params):
    return _has(params, is_var)


class FunctionFactory:
    """Generate python functions for all variety of allowed signatures."""

    def __init__(self, arg_name_pool, default_pool):
        self.name_pool = arg_name_pool
        self.default_pool = itt.cycle(default_pool)

    def __call__(self, n_par_kind, name_base='f', class_name_base=None):
        """
        Generate functions with signature based on *n_par_kind*. Successively
        yields fuctions having between 0 and n parameters of each kind, where n
        is an integer given in *n_par_kind* for that kind of parameter.

        Parameters
        ----------
        n_par_kind : dict
            Maximum number of parameters of each kind for function arg spec. 
            Kind is the integer code is `inspect._ParameterKind`.
        name_base : str, optional
            Stem for names given to functions, by default 'f'. A sequence number
            is appended to each successive function.
        class_name_base : str, optional
            Name of the class in which the function will be defined.  If None,
            the default, a function is created. If given, a method is created
            in the class with this name. 

        Yields
        -------
        function or method
        """

        i = 0
        for nargs in itt.product(*(range(n + 1) for n in n_par_kind.values())):
            for params in self.gen_params(nargs):
                i += 1

                if class_name_base:
                    class_name = f'{class_name_base}{i}'
                    name = name_base
                else:
                    class_name = None
                    name = f'{name_base}{i}'

                # create func
                yield self.make(name, params, class_name)

        logger.info(
            f'Created {i} functions with unique signature')

    def gen_params(self, nkind):
        """
        Generate parameters for the function signature.

        Parameters
        ----------
        nkind : dict
            Maximum of parameters of each kind.

        Yields
        -------
        list
            List of `inspect.Parameter`s for function
        """
        name_pool = itt.cycle(self.name_pool)
        name_generators = {POS: name_pool,
                           PKW: name_pool,
                           VAR: itt.repeat('args'),
                           KWO: name_pool,
                           VKW: itt.repeat('kws')}

        params_by_type = defaultdict(list)
        for kind, n in zip(PKIND, nkind):
            for _ in range(n):
                name = next(name_generators[kind])
                params_by_type[kind].append(
                    Parameter(name, kind)
                )

        # for positional args: non-default argument cannot follow default
        # argument (unless non-default is kw-only parameter)
        # Eg: this is OK:
        # >>> def foo(a=1, *, b):
        # ...    pass
        #
        # BUT this is a SyntaxError
        # >>> def foo(a=1, /, b):
        # ...     pass

        parts = defaultdict(list)
        params_by_type[POS].extend(params_by_type.pop(PKW, []))
        for kind in PKIND:
            # toggle defaults on / off
            params = params_by_type.get(kind, [])
            parts[kind].extend(self.toggle_defaults(params))

        for params in itt.product(*parts.values()):
            yield list(mit.flatten(params))

    def toggle_defaults(self, params):
        """Toggle defaults on / off for function parameters *params*"""
        # copy
        # params = params[:]

        yield params

        if not len(params):
            return

        last = params[-1]
        if is_var(last):
            # variadic args don't admit defaults
            return

        # new parameter with default
        for params in self.toggle_defaults(params[:-1]):
            yield params + [last.replace(default=next(self.default_pool))]

    @staticmethod
    def get_code(name, params, class_name=None):
        """function source code factory"""
        if class_name:
            params = [Parameter('self', POS)] + params

        sig = inspect.Signature(params)
        s = txw.dedent(f"""
                        def {name}{sig!s}:
                            pass
                        """).strip('\n')

        if class_name:
            deffunc = txw.indent(s, '\t')
            defclass = f"class {class_name}:\n{deffunc}".expandtabs(4)
            return f'{defclass}\n\nobj = {class_name}()'
        return s

    def make(self, name, params, class_name=None):
        """function factory"""
        locals_ = {}
        exec(self.get_code(name, params, class_name), None, locals_)
        if class_name:
            return getattr(locals_['obj'], name)
        return locals_[name]


class ArgValGen:
    """Generate random parameter values for function with any signature"""

    # TODO: could be a class that takes the function as input.
    # TODO: use annotations to generate randoms by type

    def __init__(self, arg_pool, var_pool, kws_pool):
        self.arg_pool = itt.cycle(arg_pool)
        self.var_pool = itt.cycle(var_pool)
        self.kws_pool = itt.cycle(kws_pool)

    def __call__(self, fun):

        sig = inspect.signature(fun)
        params = sig.parameters

        req = defaultdict(list)
        for p in params.values():
            req[is_required(p)].append(p)

        args, kws = self.get_vals(req[True])
        yield tuple(args), kws.copy()

        # split non-required parameters by kind
        by_kind = defaultdict(list)
        for p in req[False]:
            by_kind[p.kind].append(p)

        # if one of POS is omitted (ie takes default), cannot specify any of the
        # others, or VAR args
        # conversely if VAR is specified, cannot omit any POS or PKW

        # for PKW, if VAR is specified, need to specify these in args
        # params = [p for p in by_kind.pop(kind, []) for kind in (POS, PKW, VAR)]

        for kind in (POS, PKW, VAR):
            for p in by_kind.pop(kind, []):
                self.get_val(p, args, kws)
                yield tuple(args), kws

        params = []
        list(map(params.extend, by_kind.values()))
        for p in params:
            self.get_val(p, args, kws)
            yield args, kws.copy()

    def get_vals(self, params, args=None, kws=None):
        args = args or []
        kws = kws or {}
        for p in params:
            self.get_val(p, args, kws)
        return args, kws

    def get_val(self, par, args, kws):
        if par.name == 'self':
            return

        if par.kind == POS:
            args.append(next(self.arg_pool))

        elif par.kind == PKW:
            # kws[par.name] = next(self.arg_pool)
            args.append(next(self.arg_pool))

        elif par.kind == VAR:
            args.extend(next(self.var_pool))

        elif par.kind == KWO:
            kws[par.name] = next(self.arg_pool)

        elif par.kind == VKW:
            kws.update(next(self.kws_pool))


# ---------------------------------------------------------------------------- #
# Helper class
class FuncHelper:
    def __init__(self, fun):
        self.fun = fun
        self.sig = str(inspect.signature(fun))


# ---------------------------------------------------------------------------- #
# Create Functions
SPEC = {POS: 1,
        PKW: 1,
        VAR: 1,
        KWO: 1,
        VKW: 1}


factory = FunctionFactory('abc', range(5))(SPEC)
helpers = [*map(FuncHelper, factory)]

avg = ArgValGen(arg_pool=[1, 2, 3, 4, 5],
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


REGEX_PARAMS = re.compile(r'((?P<name>\w+)(?:=(?P<default>.+?))?),')
#


@parametrize(fun=helpers, idgen='{fun.fun.__name__}')
def test_caller_basic(fun):
    # check if we are faithfully reproducing the signature
    # builtin signature rep prints trailing PEP570 / marker which is meaningless
    try:
        sig = replace_suffix(fun.sig, ', /)', ')')
        assert pp.caller(fun.fun).endswith(sig)
    except Exception as err:
        from IPython import embed
        import textwrap, traceback
        embed(header=textwrap.dedent(
                f"""\
                Caught the following {type(err).__name__}:
                %s
                Exception will be re-raised upon exiting this embedded interpreter.
                """) % traceback.format_exc())
        raise
        


@parametrize(
    'fun, spec',
    ((fun, spec) for fun in helpers for spec in avg(fun.fun)),
    idgen='{fun.fun.__name__}{spec}'
)
def test_caller_defaults(fun, spec):
    # check if defaults are represented / dropped
    args, kws = spec
    d = pp.caller(fun.fun, args, kws, show_defaults=True)
    xd = r = pp.caller(fun.fun, args, kws, show_defaults=False)
    for i, arg in enumerate(REGEX_PARAMS.finditer(fun.sig)):
        if arg['default']:
            if (len(args) > i and args[i]) or (arg['name'] in kws):
                # value specified
                pass
            else:
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