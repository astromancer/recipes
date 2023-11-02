"""
Pretty printing callable objects and call signatures.
"""

# std
import inspect
import textwrap as txw
import functools as ftl

# relative
from ..introspect.utils import get_module_name


# ---------------------------------------------------------------------------- #
POS, PKW, VAR, KWO, VKW = list(inspect._ParameterKind)
VAR_MARKS = {VAR: '*', VKW: '**'}
_empty = inspect.Parameter.empty

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


def parameter(par, val_formatter=repr):
    kind = par.kind
    formatted = par._name

    # Add annotation and default value
    if par._annotation is not _empty:
        formatted = f'{formatted}: {inspect.formatannotation(par._annotation)}'

    if par._default is not _empty:
        space = ' ' * (par._annotation is not _empty)
        formatted = '{0}{2}={2}{1}'.format(
            formatted, val_formatter(par._default), space)

    return VAR_MARKS.get(kind, '') + formatted


def caller(obj, args=(), kws=None, show_defaults=True,
           show_binding_class=True, name_depth=2,
           params_per_line=None, hang=None, wrap=80,
           value_formatter=repr):
    """
    Pretty format a callable object, optionally with paramater values for
    representing the call signature.

    This is a flexible formatter for producing string representations of call
    signatures for any callable python object. Optional `args` and `kws`
    parameters allows one to print the values of parameters as they would be
    passed to the function. A switch for printing the default parameter values
    is also available in `show_defaults`. This function can therefore be used to
    represent callable objects themselves, ie. the function without parameters,
    or a call signature ie. how the call will be seen by the interpreter.

    Wrapping the call signature across multiple lines for calls with many
    parameters, is also supported, as is fine tuning parameters for the depth of
    the function name representation, indentation, and placement of the opening
    and closing brackets.


    Parameters
    ----------
    obj : object
        A callable object.
    args : tuple, optional
        Positional and variadic positional arguments for the represented call,
        by default ().
    kws : dict, optional
        Variadic keywords for the call, by default None
    show_defaults : bool, optional
        Whether or not to include parameters with default values, by default
        True.
    show_binding_class : bool
        If the callable is a method, show the name of the class that the method
        is bound to, instead of the name of class which defined the method.
    name_depth : int, optional
        Controls how the function's (qualified) name is represented. This
        parameter gives the namespace depth, number of parent object names to
        include in the qualified name of the callable. The default, 1, will only
        give the object name itself. Any higher integer will include the the
        dot-seperated name(s) of the class, (sub)module(s), package, (or
        <locals>) in the name up to the requested number.
        For fully qualified names (up to (sub)module level), use
            `name_depth='module'`.
        For the full name spec up to the package level, use
            `name_depth=-1` or `name_depth='package'`.
    params_per_line : ine, optional
        Number of parameters to print per line. If None (the default) a variable
        number of parameters are printed per line while respecting requested
        *wrap* value.
    hang : bool, optional
        Whether function parameters start on a new line. The default behaviour,
        `hang=None`, chooses to hang the parameter spec (if *params_per_line*
        not given) if the number of parameters in the call is greater than 7, or
        if one of the parameters has a long repr.
    wrap : int, optional
        Line width for hard wrapping, by default 80.
    value_formatter : callable, optional
        Function to use for formatting parameter values, by default repr.

    Examples
    --------
    >>>

    Returns
    -------
    str
        A string representing the callable object signature.

    Raises
    ------
    TypeError
        If the object is not callable.
    """
    # todo ppl
    # TODO: option to not print param names
    # TODO: safety limit for large parameter values
    #           : safe_repr
    # TODO: interject str formatter for types eg. np.ndarray?
    # TODO: colourise elements  / defaults / non-defaults
    #

    if not callable(obj):
        raise TypeError(f'Object {obj} is not a callable.')

    # mutable default
    kws = kws or {}

    # special handling for partial objects!
    if partial := isinstance(obj, ftl.partial):
        obj = obj.func
        args = (*obj.args, *args)
        kws = {**obj.keywords, **kws}

    name = get_name(obj, name_depth, show_binding_class)
    if partial:
        name = f'functools.partial({name})'

    # format signature
    sig = signature(inspect.signature(obj), args, kws,
                    wrap, (n := len(name)) + 1, params_per_line,
                    hang, show_defaults, value_formatter)
    return name + sig.replace('\n', f'{" ":<{n}}\n')


def get_name(obj, name_depth, show_binding_class=True):
    # get object name string with module
    if not name_depth:
        return ''

    if hasattr(obj, '__qualname__'):
        name = obj.__qualname__
    else:
        kls = type(obj)
        name = f'{kls.__module__}{kls.__name__}'

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
        module_name = get_module_name(obj, name_depth - local_depth)
        name_parts = module_name.split('.') + name_parts

    # full name to specified depth
    return '.'.join(filter(None, name_parts))


def signature(sig, args=(), kws=None, wrap=80, indent=1,
              params_per_line=None, hang=None, show_defaults=True,
              value_formatter=repr, pep570_marks=True):

    # format each parameter as 'param=value' pair
    if (args or kws):
        # with parameter values provided
        ba = sig.bind_partial(*args, **(kws or {}))
        if show_defaults:
            ba.apply_defaults()
        pars = ['='.join((p, value_formatter(val)))
                for p, val in ba.arguments.items()]
        if not pars:
            return '()'
    else:
        # This prints the function signature with default values
        pars = sig.parameters

        if not show_defaults:
            # drop parameters which have defaults
            pars = {name: par
                    for name, par in pars.items()
                    if par.default == par.empty}

        if not pars:
            return '()'

        # format individual paramter value pairs
        pars, kinds = zip(*((parameter(p, value_formatter), p.kind)
                            for p in pars.values()))
        pars = list(pars)

        # inject special / and * markers PEP570
        # NOTE: this is OK
        # >>> def foo(a, /, *, b):
        # ...   pass
        # BUT this is a syntax error
        # >>> def foo(a, *, /, b):
        # ...   pass
        if pep570_marks:
            add = 0
            if (POS in kinds) and (len(set(kinds)) > 1):
                # everything preceding / is position only
                pars.insert(kinds.index(POS) + 1, '/')
                add = 1

            if (KWO in kinds) and (VAR not in kinds):
                # everything following * in keyword only
                pars.insert(kinds.index(KWO) + add, '*')

    # format!

    # item_widths = list(map(len, pars))
    widest = max(map(len, pars))

    # get default choices for repr
    ppl = params_per_line
    if ppl:
        ppl = int(params_per_line)
        wrap = False
    # elif wrap:
    #     ppl = max(wrap // widest, 1)
    # else:
    #     ppl = 100
    # ppl = ppl or 100

    #
    # indent = len(name) + 1
    if hang is None:
        hang = ((not ppl and len(pars) > 7)
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
    for i, v in enumerate(pars):
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


# alias
pformat = method = caller
