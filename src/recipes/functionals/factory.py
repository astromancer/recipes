"""
Helpers for making functions with various signatures for testing

The following code shows (implicitly) how the various types of parameters are 
defined:

>>> def func(
...         a, b=0,     # positional only
...         /,          # mark end of position-only params
...         c, d=2,     # positional or keyword
...         *args,      # variadic positional
...         *,          # mark start of keyword-only params
...         e=3,        # keyword-only
...         **kws       # variadic keywords
...     ): ...
"""


# std
import inspect
import textwrap as txw
import itertools as itt
from collections import defaultdict

# third-party
import more_itertools as mit
from loguru import logger


# ---------------------------------------------------------------------------- #

Parameter = inspect.Parameter
PKIND = POS, PKW, VAR, KWO, VKW = list(inspect._ParameterKind)


NULL = object()

FUNC_TEMPL = """
def {name}{sig!s}:
    ...
"""

# pylint: disable-all


# TODO: generate function from choices from below


# argspec = {POS: (name_pool, default_pool),
#            PKW: (name_pool, default_pool),
#            VAR: (itt.repeat('*args'), itt.repeat(Parameter.empty)),
#            KWO: (name_pool, default_pool),
#            VKW: (itt.repeat('**kws'), itt.repeat(Parameter.empty))}

# # varspec = {VAR: (itt.repeat('*args'), itt.repeat(Parameter.empty)),
#            VKW: (itt.repeat('**kws'), itt.repeat(Parameter.empty))}

# ---------------------------------------------------------------------------- #
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

    def __init__(self, arg_name_pool, default_pool, function_body='...'):
        self.name_pool = arg_name_pool
        self.default_pool = itt.cycle(default_pool)
        self.function_body = str(function_body)

    def __call__(self, n_par_kind, name_base='f', class_name_base=None, body=None):
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
                yield self.make(name, params, class_name, body)

        logger.info(f'Created {i} functions with unique signature.')

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
            yield [*params, last.replace(default=next(self.default_pool))]

    @staticmethod
    def get_code(name, params, class_name=None, body=None):
        """function source code factory"""
        if class_name:
            params = [Parameter('self', POS)] + params

        sig = inspect.Signature(params)
        body = txw.indent(body or '...', ' ' * 4)
        s = txw.dedent(FUNC_TEMPL.format(**locals())).strip('\n')

        if class_name:
            deffunc = txw.indent(s, ' ' * 4)
            defclass = f'class {class_name}:\n{deffunc}'
            return f'{defclass}\n\nobj = {class_name}()'
        
        return s

    def make(self, name, params, class_name=None, body=None, evaldict=None):
        """function factory."""
        locals_ = {}
        code = self.get_code(name, params, class_name, body or self.function_body)
        # print('CODE', code, sep='\n')
        exec(code, evaldict or {}, locals_)
        return getattr(locals_['obj'], name) if class_name else locals_[name]


class ParamValueGenerator:
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

        if par.kind in [POS, PKW]:
            if (item := next(self.arg_pool, NULL)) is not NULL:
                args.append(item)

        elif par.kind == VAR:
            args.extend(next(self.var_pool, ()))

        elif par.kind == KWO:
            if (item := next(self.arg_pool, NULL)) is not NULL:
                kws[par.name] = item

        elif par.kind == VKW:
            kws.update(next(self.kws_pool, {}))


ArgValGen = ParamValueGenerator
