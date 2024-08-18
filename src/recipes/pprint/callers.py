"""
Pretty printing callable objects and call signatures.
"""

# std
import inspect
import textwrap as txw
import itertools as itt
import functools as ftl
import contextlib as ctx

# relative
from .. import string
from ..oo import slots
from ..containers import dicts
from ..oo.represent import DEFAULT_STYLE
from ..introspect.utils import get_module_name
from .dispatch import pformat as default_formatter


# ---------------------------------------------------------------------------- #
# TODO: safety limit for large parameter values
#           : safe_repr
# TODO: colourise elements  / defaults / non-defaults

# ---------------------------------------------------------------------------- #
# Module constants
DEFAULT = object()
EMPTY = inspect.Parameter.empty
POS, PKW, VAR, KWO, VKW = list(inspect._ParameterKind)
VAR_MARKS = {VAR: '*', VKW: '**'}


# ---------------------------------------------------------------------------- #
def isempty(obj):
    return obj is EMPTY


def _var_name(par):
    return f'{VAR_MARKS.get(par.kind, "")}{par._name}'

# ---------------------------------------------------------------------------- #


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

class BaseFormatter(slots.SlotHelper):

    __slots__ = ('_parent', )
    _repr_style = {**DEFAULT_STYLE, 'hang': True}

    def __init__(self, *args, parent=None, **kws):
        super().__init__(*args, **kws)
        self._parent = parent

    def __str__(self):
        return self.format()

    def __call__(self, *args, **kws):
        return self.format(*args, **kws)

    def format(self, *args, **kws):
        raise NotImplementedError


class Parameter(BaseFormatter):
    # Paramater formatter

    __slots__ = ('lhs', 'equal', 'rhs', 'align')

    def __init__(self, lhs=str, equal='=', rhs=default_formatter, align=False):
        # save local state on instance
        super().__init__(**slots.sanitize(locals()))

    def format(self, par, name=True, annotated=None, value=DEFAULT, width=0, indent=True):
        return ''.join(self._parts(par, name, annotated, value, width, indent))

    def name(self, par, name=True):
        # get name
        if name is None:
            # default is only name keyword-only
            name = par.kind is KWO

        if name is True:
            # add prefix '*' / '**'
            name = f'{VAR_MARKS.get(par.kind, "")}{par._name}'

        # Fill empty if name is null
        name = name or ''
        return name

    def annotation(self, anno):
        return inspect.formatannotation(anno)

    def _parts(self, par, name, annotated, value, width, indent):
        # get formatted "name(:annotation)(=value)" and value for
        # name value pair (par, value)

        # self._parent._parent : Signature / Invocation

        # get name
        name = self.name(par, name)
        assert isinstance(name, str)

        # if par.kind is VKW:

        # fill default if no value given
        if value is DEFAULT:
            # default is to print annotation only when parameter takes default value
            value = par.default
            annotated = (annotated is None)

        # add annotation if meaningful
        if name and annotated and (par._annotation is not EMPTY):
            name = f'{name}: {self.annotation(par._annotation)}'

        return self._align(name, value, width, indent)

    def _align(self, lhs, rhs, width, indent):
        # get formatted name (possibly with annotation and equal) and value for
        # key value pair (lhs, rhs)
        lhs = lhs or ''
        have_value = not isempty(rhs)
        eq = self.equal if (lhs and have_value) else ''

        if align := self.align:
            if align == '<':
                lhs = f'{lhs + eq: <{width}}'
            elif align == '>':
                lhs = f'{lhs: <{width - len(eq)}}{eq}'
        else:
            lhs += eq

        # indent rhs
        if indent in (True, None):
            indent = len(lhs)
        
        rhs = string.indent(self.rhs(rhs), indent) if have_value else ''
        #                                  ^ width + indent ?
        
        
        return lhs, rhs


class ParameterList(BaseFormatter):

    __slots__ = ('ppl', 'wrap', 'indent', 'hang', 'align', 'parameter')  # fmt?

    def __init__(self, ppl=None, align=False, wrap=80, indent=None, hang=None, **kws):

        # parameter formatter
        parameter = Parameter(align=align, **kws)
        parameter._parent = self

        # save local state on instance
        super().__init__(**slots.sanitize(locals()))

    def format(self, params, indent=None, **fmt):
        # parameters as block wrapped string
        if not params:
            return

        params = list(self._parts(params, **fmt))
        return self.wrapped(params, indent)

    def _parts(self, params, names=True, values=(), width=None, indent=None, **fmt):
        # yield formatted parameter(:annotation)(=value) strings

        assert (not values) or (len(values) == len(params))

        if not params:
            return

        if self.align and width is None:
            if not names:
                # format lhs only first
                names, _ = zip(*(self.parameter._parts(p, value=EMPTY, **fmt) 
                                 for p in params))

            # get width (widest name)
            width = string.width(names)

        # now format rhs values indented at width of lhs =
        width = width or 0
        if names in (True, None, False):
            names = [names] * len(params)

        for par, name, value in itt.zip_longest(params, names, values, fillvalue=DEFAULT):
            if not name:
                # unpack variadics in invocation
                if (par.kind is VAR):
                    yield from map(self.parameter.rhs, value)
                    continue

            # format
            s = self.parameter(par, name=name, value=value, width=width, **fmt)

            # indent variadic kws dict
            if (par.kind is VKW):
                name = self.parameter.name(par)

                # indent multiline parameters to width of parameter name
                s = s.replace('\n', '\n' + ' ' * (len(name) + 1))

            yield s

    # ------------------------------------------------------------------------ #
    def wrapped(self, params, indent=None):

        if not params:
            return '()'

        ppl = self.ppl
        wrap = self.wrap
        indent = indent or self.indent
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


class Formatter(BaseFormatter):
    """
    Pretty format call signatures and invocations.
    """

    __slots__ = ('show_binding_class', 'name_depth', 'parameters')

    def __init__(self, name_depth=2, show_binding_class=True, **kws):

        # parameter list fomatter
        parameters = ParameterList(**kws)
        parameters._parent = self

        # save local state on instance
        super().__init__(**slots.sanitize(locals()))

    def __call__(self, obj, **kws):
        return Signature(obj, **kws)

    def name(self, obj):
        return get_name(obj, self.name_depth, self.show_binding_class)


# ---------------------------------------------------------------------------- #
class Callable(slots.SlotHelper):
    """
    A class for representing callable objects and call invocations as strings.
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

            try:
                sig = inspect.signature(obj, follow_wrapped=False)
            except ValueError:
                if obj := getattr(obj, '__call__', ()):
                    sig = inspect.signature(obj, follow_wrapped=False)
                else:
                    raise

            fmt = Formatter(*args, **kws)
            state = slots.sanitize(locals(), 'args')

        # save local state on instance
        super().__init__(**state)

    def __call__(self, *args, **kws):
        args, kws = self._get_args_kws(*args, **kws)
        return Signature(self)(*args, **kws)

    def _get_args_kws(self, *args, **kws):
        obj = self.obj

        # special handling for partial objects!
        if self.partial:
            args = (*obj.args, *args)
            kws = {**obj.keywords, **kws}

        return args, kws

    def format(self, *params, **fmt):
        return f'{self.name()}{self.parameters(*params, **fmt)}'

    # ------------------------------------------------------------------------ #
    def name(self):
        name = self.fmt.name(self.obj)

        if self.partial:
            return f'functools.partial({name})'

        return name

    # ------------------------------------------------------------------------ #
    # def _parameter(self, par, *args, **kws):
    #     return self.fmt.parameters.parameter._parts(par, *args, **kws)

    # def parameter(self, par, *args, **kws):
    #     return ''.join(self._parameter(par, *args, **kws))

    def _parameters(self, *args, **kws):
        return self.fmt.parameters._parts(*args, **kws)

    def parameters(self, *args, indent=None, hang=None, **kws):

        name = self.name()
        plist = list(self._parameters(*args, **kws))

        widest = max(map(len, plist))

        ppl = self.fmt.parameters.ppl
        wrap = self.fmt.parameters.wrap
        indent = indent or self.fmt.parameters.indent
        hang = self.fmt.parameters.hang

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
            hang = ((not ppl and len(plist) > 7)
                    or
                    (wrap and indent and (widest > wrap - indent)))

        hang = bool(hang)

        if indent is None:
            indent = 4 if hang else len(name) + 1

        return self.fmt.parameters.wrapped(plist, indent)


class Signature(Callable):

    def __call__(self, *args, **kws):
        return Invocation(self, args, kws)

    def _get_args_kws(self, *_, **__):
        return super()._get_args_kws()

    def format(self, annotated=True, show_defaults=True, pep570_marks=True):
        # This prints the function signature [optionally with default valus]
        # TODO: return annotation

        return super().format(annotated=annotated,
                              show_defaults=show_defaults,
                              pep570_marks=pep570_marks)

    # ------------------------------------------------------------------------ #
    def annotation(self, anno):
        return inspect.formatannotation(anno)

    # def parameter(self, par, annotated=None, value=DEFAULT, width=0):
    #     # get formatted name (possibly with annotation and equal) and value for
    #     # name value pair (par, value)
    #     # prefix '*' / '**'
    #     name = f'{VAR_MARKS.get(par.kind, "")}{par._name}'
    #     return self._parameter(par, name, annotated, value, width)

    def _parameters(self, annotated, show_defaults, pep570_marks, indent=None):
        # yield formatted parameter(:annotation)(=value) string

        params = self.sig.parameters.values()

        if not show_defaults:
            # drop parameters which have defaults
            params = [par for par in params if par.default == EMPTY]

        # add prefix '*' / '**'
        # names = {_var_name(p): p for p in params.values()}

        # Get mapping: formatter parameter name (possibly with annotation) -> default value
        formatted = list(self.fmt.parameters._parts(params, annotated=annotated,
                                                    indent=indent))

        if pep570_marks:
            yield from self._pep570(params, formatted)
            return

        yield from formatted

    def _pep570(self, params, formatted):
        """
        inject special / and * markers PEP570
        everything preceding / is position only
        everything following * in keyword only
        """

        # NOTE: this is OK
        # >>> def foo(a, /, *, b): ...

        # ALSO OK:
        # >>> def x(*, q): ...

        # ALSO OK
        # >>> def x(a, /, q): ...

        # BUT this is a syntax error
        # >>> def foo(a, *, /, b): ...

        formatted = list(formatted)
        kinds = [p.kind for p in params]

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
    """Formatter for call invocations."""

    __slots__ = ('args', 'kws')

    def __init__(self, obj, args=(), kws=None, /, **fmt):
        super().__init__(obj, **fmt)
        self.args = args
        self.kws = dict(kws or {})

    def format(self, param_names=True, show_defaults=True):
        # format each parameter as 'param=value' pair
        return super().format(param_names=param_names,
                              show_defaults=show_defaults)

    # def parameter(self, par, name=None, value=DEFAULT, width=0):
    #     return super().parameter(par, name, False, value, width)

    def _parameters(self, param_names=True, show_defaults=True):

        # with parameter values provided
        ba = self.sig.bind_partial(*self.args, **self.kws)

        if show_defaults:
            # set default values for missing arguments.
            ba.apply_defaults()

        if not ba.arguments:
            # this means the function takes no parameters
            return

        # Get mapping: formatter parameter name -> value
        params = self.sig.parameters
        params = [params[name] for name in ba.arguments]

        yield from self.fmt.parameters._parts(params, param_names, ba.arguments.values())

        # yield from super()._parameters(params, ba.arguments.values(), name=named)


# ---------------------------------------------------------------------------- #
#
FORMATTER_KWS = {slot
                 for kls in (Formatter, ParameterList, Parameter)
                 for slot in kls.__slots__} - {'parameter', 'parameters'}


# @api.synonyms({'params_per_line': 'ppl'}, action='silent')
def caller(obj, args=EMPTY, kws=EMPTY, **fmt):

    # split Formatter init params
    fmt_call_kws, fmt_init_kws = dicts.split(fmt, FORMATTER_KWS)

    formatter = Signature(obj, **fmt_init_kws)
    no_args = (args is EMPTY)
    no_kws = (kws is EMPTY)
    if no_args and no_kws:
        # format as signature
        return formatter.format(**fmt_call_kws)

    if no_args:
        args = ()

    if no_kws:
        kws = {}

    # format as invocation
    invocation = formatter(*args, **kws)
    return invocation.format(**fmt_call_kws)


# ---------------------------------------------------------------------------- #
# aliases
pformat = method = caller
