"""
Pretty printing callable objects and call signatures.
"""

# std
import inspect
import textwrap as txw
import functools as ftl
import contextlib as ctx

# relative
from .. import api, dicts
from ..iter import cofilter
from ..string import indent as indented
from ..introspect.utils import get_module_name
from ..oo.slots import SlotHelper, _sanitize_locals


# ---------------------------------------------------------------------------- #
# module constants
POS, PKW, VAR, KWO, VKW = list(inspect._ParameterKind)
VAR_MARKS = {VAR: '*', VKW: '**'}

_default = object()

# ---------------------------------------------------------------------------- #


def isempty(obj):
    return obj is inspect.Parameter.empty


def describe(obj, sep=' ', repr=repr):
    """
    Object type and fully qualified name.

    Parameters
    ----------
    obj : callable
        Any callable object
    sep : str
        Character(s) separating object class name and qualname

    Examples
    --------
    >>> describe(str)
    "class 'str'"

    >>> describe(id)
    "builtin_function_or_method 'id'"

    >>> class X:
    ...     def __call__(self):
    ...         pass

    >>> describe(X)
    "class '__main__.X'"

    >>> describe(X())
    "instance of class '__main__.X'"

    Returns
    -------
    str
        Description of `obj` type and its name.
    """
    assert callable(obj)

    if isinstance(obj, type):
        if obj.__module__ == 'builtins':
            return f'class {repr(obj.__name__)}'

        # obj is a class
        return f"class {repr(f'{obj.__module__}.{obj.__name__}')}"
        # return str(obj).strip("<>")

    if hasattr(obj, '__qualname__'):
        # any function or method
        # TODO: distinguish between functions and methods
        # if get_defining_class(obj):
        #     ' method'
        return f'{obj.__class__.__name__}{sep}{repr(obj.__qualname__)}'

    # any other callable
    return f'instance of{sep}{describe(type(obj), repr=repr)}'


def get_name(obj, name_depth, show_binding_class=True):
    # get object name string with module
    if not name_depth:
        return ''

    if hasattr(obj, '__qualname__'):
        name = obj.__qualname__
    else:
        kls = type(obj)
        name = f'{kls.__module__}.{kls.__name__}'

    if show_binding_class and name_depth > 1 and hasattr(obj, '__self__'):
        defining_class_name, _ = name.split('.', 1)
        name = name.replace(defining_class_name, obj.__self__.__class__.__name__)

    name_parts = name.split('.')
    local_depth = len(name_parts)
    name_depth = 100 if name_depth == -1 else name_depth
    if name_depth < local_depth:
        name_parts = name_parts[-name_depth:]
    else:
        # prepend (sub)module/package names
        module_name = ''
        with ctx.suppress(TypeError):
            module_name = get_module_name(obj, name_depth - local_depth)
        name_parts = module_name.split('.') + name_parts

    # full name to specified depth
    return '.'.join(filter(None, name_parts))


# ---------------------------------------------------------------------------- #
# Formatter


# @api.synonyms({'params_per_line': 'ppl'}, action='silent')
# def format(self, args=(), kws={},
#             show_binding_class=True, name_depth=2,
#             **fmt):
#     """
#     Pretty format call signatures and invocations with parameter values.

#     This is a flexible formatter for producing string representations of call
#     signatures for any callable python object. Optional `args` and `kws`
#     parameters allows formatting the parameter values as they would be passed
#     through by the interpreter. This function can therefore be used to represent
#     callable objects themselves, ie. the function without parameters, or a call
#     invocation pattern, i.e. how the call would made by the interpreter.

#     Switches for optionally including:
#         - parameter default values:                            `show_defaults`
#         - parameter kind specifiers (PEP570) in the signature: `pep570_marks`
#         - parameter annotations:                               `annotated`

#     Wrapping the call signature across multiple lines for calls with many
#     parameters, is also supported, as is fine tuning parameters for the depth of
#     the function name representation, indentation, and placement of the opening
#     and closing brackets.


#     Parameters
#     ----------
#     obj : object
#         A callable object.
#     args : tuple, optional
#         Positional and variadic positional arguments for the represented call,
#         by default ().
#     kws : dict, optional
#         Variadic keywords for the call, by default None
#     show_defaults : bool, optional
#         Whether or not to include parameters with default values, by default
#         True.
#     pep570: bool
#         Add (position-only '*, '/' keyword-only) markers
#     show_binding_class : bool
#         If the callable is a method, show the name of the class that the method
#         is bound to, instead of the name of class which defined the method.
#     name_depth : int, optional
#         Controls how the function's (qualified) name is represented. This
#         parameter gives the namespace depth, number of parent object names to
#         include in the qualified name of the callable. The default, 1, will only
#         give the object name itself. Any higher integer will include the the
#         dot-seperated name(s) of the class, (sub)module(s), package, (or
#         <locals>) in the name up to the requested number.
#         For fully qualified names (up to (sub)module level), use
#             `name_depth='module'`.
#         For the full name spec up to the package level, use
#             `name_depth=-1` or `name_depth='package'`.
#     ppl : int, optional
#         Number of parameters to print per line. If None (the default) a variable
#         number of parameters are printed per line while respecting requested
#         *wrap* value.
#     hang : bool, optional
#         Whether function parameters start on a new line. The default behaviour,
#         `hang=None`, chooses to hang the parameter spec (if *ppl*
#         not given) if the number of parameters in the call is greater than 7, or
#         if one of the parameters has a long repr.
#     wrap : int, optional
#         Line width for hard wrapping, by default 80.
#     rhs : callable, optional
#         Function to use for formatting parameter values, by default repr.

#     Examples
#     --------
#     >>>

#     Returns
#     -------
#     str
#         A string representing the callable object signature.

#     Raises
#     ------
#     TypeError
#         If the object is not callable.
#     """

# TODO: option to not print param names
# TODO: safety limit for large parameter values
#           : safe_repr
# TODO: colourise elements  / defaults / non-defaults

class Formatter(SlotHelper):
    """
    Pretty format call signatures and invocations.
    """

    __slots__ = ('lhs', 'equal', 'rhs', 'align',
                 'ppl', 'wrap', 'indent', 'hang')

    def __init__(self, name_depth=2, show_binding_class=True,
                 lhs=str, equal='=', rhs=None, align=False,
                 ppl=None, wrap=80, indent=True, hang=None):

        if rhs is None:
            from recipes.pprint import pformat as rhs

        # save local state on instance
        super().__init__(**_sanitize_locals(locals()))

    def __call__(self, obj, **kws):
        return Signature(obj, **kws)

    def name(self, obj):
        return get_name(obj, self.name_depth, self.show_binding_class)

    # ------------------------------------------------------------------------ #
    def _align(self, text, width):

        if self.align == '<':
            return f'{text + self.equal: <{width}}'

        if self.align == '>':
            return f'{text: <{width}}{self.equal}'

        return f'{text}{self.equal}'

    def _wrap(self, params):

        ppl = self.ppl
        wrap = self.wrap
        indent = self.indent
        hang = self.hang

        # format!
        widest = max(map(len, params))

        # get default choices for repr
        if ppl:
            ppl = int(ppl)
            wrap = False
        # elif wrap:
        #     ppl = max(wrap // widest, 1)
        # else:
        #     ppl = 100
        # ppl = ppl or 100

        #
        # indent = len(name) + 1
        if hang is None:
            hang = ((not ppl and len(params) > 7)
                    or
                    (wrap and widest > wrap - indent))

        hang = bool(hang)
        if hang:
            indent = 4

        if wrap:
            wrap -= indent

        # if widest > wrap:
        #     # truncate!!
        #     pass

        ppl = ppl or 100

        # make the signature rep
        s = ''
        line = ''
        for i, v in enumerate(params):
            if i > 0:
                line += ', '

            if ((i % ppl) == 0) or (wrap and (len(line) + len(v) > wrap)):
                s += f'{line}\n'
                line = v
            else:
                line += v

            # if len(s) > wrap:
            #     # FIXME: this will break in the middle of **kws or *args etc...
            #     s = '\n'.join(txw.wrap(s, wrap))
        s += line
        s = txw.indent(s, ' ' * indent).lstrip('\n')

        s = f'\n{s}\n' if hang else s.lstrip()
        return s.join('()')


class Callable(SlotHelper):
    """
    A wrapper class for formatting callable objects and represent call
    invocations.
    """

    __slots__ = ('obj', 'sig', 'partial', 'fmt')

    def __init__(self, obj, *args, **kws):
        # args, kws passed to formatter

        if isinstance(obj, Callable):
            # internal state
            state = obj.__getstate__()
        else:
            if not callable(obj):
                raise TypeError(f'Object {obj} is not a callable.')

            if partial := isinstance(obj, ftl.partial):
                obj = obj.func

            sig = inspect.signature(obj, follow_wrapped=False)
            fmt = Formatter(*args, **kws)
            state = _sanitize_locals(locals(), 'args')

        # save local state on instance
        super().__init__(**state)

    def __call__(self, *args, **kws):

        formatter = Signature(self)
        args, kws = self._get_user_args(*args, **kws)

        if (args or kws):
            # format each parameter as 'param=value' pair
            return formatter(*args, **kws)

        return formatter

    def __str__(self):
        return self.format()

    def _get_user_args(self, *args, **kws):
        obj = self.obj

        # special handling for partial objects!
        if self.partial:
            args = (*obj.args, *args)
            kws = {**obj.keywords, **kws}

        return args, kws

    def format(self, *params, **fmt):

        name = self.name()

        if fmt.get('indent') is True:
            fmt['indent'] = len(name) + 1

        params = self.parameters(*params, **fmt)

        return f'{name}{params}'

    # ------------------------------------------------------------------------ #
    def name(self):
        name = self.fmt.name(self.obj)

        if self.partial:
            return f'functools.partial({name})'

        return name

    # ------------------------------------------------------------------------ #
    def parameters(self, *params, **fmt):
        # parameters block wrapped string
        params = self.parameter_list(*params, **fmt)

        if not params:
            return '()'

        return self.wrap(params)

    def parameter_list(self, *params, **fmt):
        # formatted list of "name(:annotation)(=value)" strings
        return list(self._parameters(*params, **fmt))

    def _parameters(self, *params, **fmt):
        # yield formatted parameter(:annotation)(=value) strings
        raise NotImplementedError

    def parameter(self, par, name=None, annotated=True, value=_default, width=0):

        if name is None:
            name = par._name

        name = f'{VAR_MARKS.get(par.kind, "")}{name}'

        lhs, rhs = self._parameter(par, name, annotated, value)

        if rhs is par.empty:
            return self.fmt.lhs(lhs)

        lhs = self.fmt._align(lhs, width)
        return f'{lhs}{indented(self.fmt.rhs(rhs), len(lhs))}'

    def _parameter(self, par, name=None, annotated=True, value=_default):

        if name is not False:
            # Add annotation and default value
            if annotated and par._annotation is not par.empty:
                name = f'{name}: {self.annotationn(par._annotation)}'

        if value is _default:
            value = par.default

        # prefix '*' / '**'
        return name, value

    def wrap(self, params):
        return self.fmt._wrap(params)


class Signature(Callable):

    def __call__(self, *args, **kws):
        return Invocation(self, args, kws)

    def _get_user_args(self, *_, **__):
        return super()._get_user_args()

    def format(self, annotated=True, show_defaults=True, pep570_marks=True):
        # This prints the function signature [optionally with default valus]
        # TODO: return annotation
        return super().format(annotated=annotated,
                              show_defaults=show_defaults,
                              pep570_marks=pep570_marks)

    # ------------------------------------------------------------------------ #
    def annotation(self, anno):
        return inspect.formatannotation(anno)

    def _parameters(self, annotated, show_defaults, pep570_marks):
        # yield formatted parameter(:annotation)(=value) string

        params = self.sig.parameters

        if not show_defaults:
            # drop parameters which have defaults
            params = {name: par
                      for name, par in params.items()
                      if par.default == par.empty}

        if not params:
            return

        # Get mapping: formatter parameter name (possibly with annotation) -> default value
        names, values = zip(*(self._parameter(p, annotated=annotated)
                              for p in params.values()))

        width = 0
        if align := self.fmt.align:
            width = max(map(len, cofilter(isempty, values, names)[1]))
            if align == '<':
                width += len(self.fmt.equal)

        # format
        values = dict(zip(params, values))
        formatted = (self.parameter(par, name, False,
                                    values.get(par._name, par.default),
                                    width)
                     for name, par in zip(names, params.values()))

        if pep570_marks:
            yield from self._pep570(params, formatted)
            return

        yield from formatted

    def _pep570(self, params, formatted):

        # inject special / and * markers PEP570
        # everything preceding / is position only
        # everything following * in keyword only

        # NOTE: this is OK
        # >>> def foo(a, /, *, b):
        # ...     pass

        # ALSO OK:
        # >>> def x(*, q):
        # ...     pass

        # ALSO OK
        # >>> def x(a, /, q):
        # ...    pass

        # BUT this is a syntax error
        # >>> def foo(a, *, /, b):
        # ...     pass

        formatted = list(formatted)
        kinds = [p.kind for p in params.values()]

        add = 0
        if POS in kinds:
            # everything preceding / is position only
            formatted.insert(kinds.index(POS) + 1, '/')
            add = 1

        if (KWO in kinds) and (VAR not in kinds):
            # everything following * in keyword only
            formatted.insert(kinds.index(KWO) + add, '*')

        return formatted


class Invocation(Callable):
    """Formatter for caall invocations."""

    __slots__ = ('args', 'kws')

    def __init__(self, obj, args=(), kws=None, /, **fmt):
        assert args or kws
        super().__init__(obj, **fmt)
        self.args = args
        self.kws = dict(kws or {})

    def format(self, show_param_names=None, show_defaults=True):
        # format each parameter as 'param=value' pair
        return super().format(show_defaults=show_defaults)

    def parameter(self, par, name=True, annotated=True, value=_default, width=0):

        if name is None:
            # default is only name keyword-only
            name = par.kind is KWO

        if name is True:
            name = f'{VAR_MARKS.get(par.kind, "")}{par._name}'

        lhs, rhs = self._parameter(par, name, annotated, value)

        if rhs is par.empty:
            return self.fmt.lhs(lhs)

        lhs = self.fmt._align(lhs, width)
        return f'{lhs}{indented(self.fmt.rhs(rhs), len(lhs))}'

    def _parameters(self, show_param_names=None, show_defaults=True):

        # with parameter values provided
        ba = self.sig.bind_partial(*self.args, **self.kws)

        if show_defaults:
            ba.apply_defaults()

        # Get mapping: formatter parameter name (possibly with annotation) -> default value
        width = 0
        if align := self.fmt.align:
            width = max(map(len, ba.arguments))
            if align == '<':
                width += len(self.equal)

        params = self.sig.parameters
        for name, value in ba.arguments.items():
            yield self.parameter(params[name], name, annotated=False,
                                 value=value, width=width)

# ---------------------------------------------------------------------------- #


@api.synonyms({'params_per_line': 'ppl'}, action='silent')
def caller(obj, args=(), kws=None, **fmt):
    invocation, fmt = dicts.split(fmt, Formatter.__slots__)
    return Callable(obj, **fmt)(*args, **(kws or {})).format(**invocation)


# ---------------------------------------------------------------------------- #
# aliases
pformat = method = caller
