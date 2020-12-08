# from recipes.decor.tests import test_cases as tcx
# pylint: disable-all

import more_itertools as mit
from collections import defaultdict
from inspect import Parameter
import sys
from recipes.introspect.imports import tidy
from recipes.decor.expose import show_func, get_module_name
import inspect
import types

import itertools as itt
import functools as ftl
import textwrap as txw
import random

random.seed(123)
# import ast

# __all__ = []

# pylint: disable-all
# Make a bunch of function definitions for testing
#
# 'a', 'a=0'
# '/',
# 'b', 'c=2'
# '*args', '*'
# 'd=3'
# '**kws'


# def IGNORE(): pass


# def ignore(o):
#     return o is IGNORE

# def is_empty(o):
#     return o is Parameter.empty


PKIND = POS, PKW, VAR, KWO, VKW = list(inspect._ParameterKind)


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


# def can_omit(par):
#     return is_var(par) or has_default(par)


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


class FunctionGenerator:
    """Generate python functions for all variety of allowed signatures"""

    def __init__(self, arg_name_pool, default_pool):
        self.name_pool = arg_name_pool
        self.default_pool = itt.cycle(default_pool)

    def __call__(self, n_par_kind, name_base='f', class_name_base=None):

        i = 0
        functions = []
        for nargs in itt.product(*(range(n + 1) for n in n_par_kind.values())):
            for params in rfg.gen_params(nargs):
                i += 1

                if class_name_base:
                    class_name = f'{class_name_base}{i}'
                    name = name_base
                else:
                    class_name = None
                    name = f'{name_base}{i}'

                # create func
                functions.append(
                    rfg.make(name, params, class_name)
                )

        return functions

    def gen_params(self, nkind):

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
        par = Parameter(last.name, last.kind, default=next(self.default_pool))

        for params in self.toggle_defaults(params[:-1]):
            yield params + [par]

    def get_code(self, name, params, class_name=None):

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
        locals_ = {}
        exec(rfg.get_code(name, params, class_name), None, locals_)
        if class_name:
            return getattr(locals_['obj'], name)
        return locals_[name]


class ArgValGen:
    """Generate random parameters for function with any signature"""

    # TODO: could be a class that takes the function as input.
    # TODO: use annotations to generate randoms by type

    def __init__(self, arg_pool, kws_pool, var_pool):
        self.arg_pool = itt.cycle(arg_pool)
        self.var_pool = var_pool
        self.kws_pool = kws_pool

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
            kws.update(self.kws_pool)


def test_show_func(fun, *spec, **kws):
    # print('Signature')
    print('show_func:', kws)
    print(show_func(fun, *spec, **kws))

    # print('\n', )
    # for spec in get_random_args(fun):
    #     print(*spec, '\n')
    #     print(
    #         show_func(fun, *spec)
    #     )



def test_expose_decor():
    @expose.args
    def foo(a, b=1, *args, c=2, **kws):
        pass

    foo(88, 12, 11, c=4, y=1)


# ----------------------------- Create Functions ----------------------------- #

# choose arg types:
rfg = FunctionGenerator('abc', range(5))
functions = rfg({POS: 1,
                 PKW: 1,
                 VAR: 1,
                 KWO: 1,
                 VKW: 1})

print(f'Created {len(functions)} functions with unique signature')


# ------------------------- Generate Random Arguments ------------------------ #

avg = ArgValGen(arg_pool=[1, 2, 3, 4, 5],
                kws_pool=dict(λ='r', x='v'),
                var_pool=gen_random_string(3))


# def inner(a, b, c):
#     pass

# p0 = ftl.partial(inner, a=1)
# p1 = ftl.partial(p0, b=2)
# p1, p0


extra = []  # [id, float, callable, tidy]
for i, fun in enumerate((functions + extra)):  #
    print('Signature')
    print(show_func(fun))
    print('--------')

    for spec in avg(fun):
        print('\nArgspec:', *spec)

        test_show_func(fun, *spec, show_defaults=False)

        if has_defaults(inspect.signature(fun).parameters):
            test_show_func(fun, *spec, show_defaults=True)

    print('=' * 80)

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


def test_expose_decor():
    @expose.args
    def foo(a, b=1, *args, c=2, **kws):
        pass

    foo(88, 12, 11, c=4, y=1)


#     # print(i)
#     # print(sig)
#     # print(ba)
#     ba.apply_defaults()
#     # print(ba)
#     print(f'{ba!s}'.replace('<BoundArguments ', fun.__qualname__).rstrip('>'))
#     # print('*'*88)

# from IPython import embed
# embed(header="Embedded interpreter at 'test_expose.py':32")
