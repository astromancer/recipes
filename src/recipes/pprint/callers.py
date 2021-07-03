"""
Pretty printing callable objects and call signatures
"""

# std libs
import inspect
import textwrap as txw

# relative libs
from ..introspect.utils import get_module_name
from ..introspect import get_class_that_defined_method
# import types


POS, PKW, VAR, KWO, VKW = list(inspect._ParameterKind)
VAR_MARKS = {VAR: '*', VKW: '**'}
_empty = inspect.Parameter.empty


def parameter(par, val_formatter=repr):
    kind = par.kind
    formatted = par._name

    # Add annotation and default value
    if par._annotation is not _empty:
        formatted = '{}: {}'.format(formatted,
                                    inspect.formatannotation(par._annotation))

    if par._default is not _empty:
        space = ' ' * (par._annotation is not _empty)
        formatted = '{0}{2}={2}{1}'.format(
            formatted, val_formatter(par._default), space)

    return VAR_MARKS.get(kind, '') + formatted


def caller(obj, args=(), kws=None, wrap=80, name_depth=1,
           params_per_line=None, hang=None, show_defaults=True,
           value_formatter=repr):
    """
    Pretty format a callable object, optionally with paramater values for the
    call signature.

    This is a flexible formatter for producing string representations of call
    signatures of any callable python object. Optional arguments allows one to
    print the parameter values of objects passed to the function. One can also
    choose whether or not to print the default parameter values. This function
    can therefore be used to represent callable objects themselves, ie. the
    function without parameters, or a call signature ie. how a call will be
    typed out in the source code.

    Wrapping the call signature across multiple lines for calls with many
    parameters, is also supported, as is fine tuning parameters for the depth of
    the function name representation, indentation, and placement of the opening
    and closing brackets.


    Parameters
    ----------
    obj : object
        The callable object
    args : tuple, optional
        Positional and variadic positional arguments for the function call, by
        default ()
    kws : dict, optional
        Variadic keywords for the call, by default None
    wrap : int, optional
        Line width for hard wrapping, by default 80
    name_depth : int, optional
        Controls how the function's name is represented. This parameter gives
        the namespace depth, number of parent object names to include in the
        qualified name of the callable. The default, 1, will only give the
        object name itself. Any higher integer will include the the
        dot-seperated name(s) of the class, (sub)module(s), package, (or
        <locals>) in the name up to the requested number.
        For fully qualified names (up to (sub)module level), use
            `name_depth='module'`.
        For the full name spec up to the package level, use
            `name_depth=-1` or `name_depth='package'`
    params_per_line : ine, optional
        Number of parameters to print per line. If None (the default) a variable
        number of parameters are printed per line while respecting requested
        *wrap* value.
    hang : bool, optional
        Whether function parameters start on a new line. The default behaviour,
        `hang=None`, chooses to hang the parameter spec (if *params_per_line*
        not given) if the number of parameters in the call is greater than 7, or
        if one of the parameters has a long repr
    show_defaults : bool, optional
        Whether or not to include parameters with default values, by default
        True.
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
        raise TypeError(f'Object {obj} is not a callable')

    # get object name string with module
    name_parts = obj.__qualname__.split('.')
    local_depth = len(name_parts)
    name_depth = 100 if name_depth == -1 else name_depth
    if name_depth < local_depth:
        name_parts = name_parts[-name_depth:]
    else:
        # prepend (sub)module/package names
        module_name = get_module_name(obj, name_depth - local_depth)
        name_parts = module_name.split('.') + name_parts

    # full name to specified depth
    name = '.'.join(filter(None, name_parts))

    # format signature
    sig = signature(inspect.signature(obj), args, kws,
                    wrap, len(name) + 1, params_per_line,
                    hang, show_defaults, value_formatter)
    return name + sig.replace('\n', (' ' * len(name)) + '\n')


def signature(sig, args=(), kws=None, wrap=80, indent=1,
              params_per_line=None, hang=None, show_defaults=True,
              value_formatter=repr, pep570_marks=True):

    # format each parameter as 'param=value' pair
    with_params = (args or kws)
    if with_params:
        # with parameter values provided
        ba = sig.bind(*args, **(kws or {}))
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

    if widest > wrap:
        # truncate!!
        pass

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

    if hang:
        s = f'\n{s}\n'
    else:
        s = s.lstrip()

    return s.join('()')

# @docsplice


def method(func, show_defining_class=True, **kws):
    """
    Get a nice string representing the method.

    Parameters
    ----------
    func: Callable
        The callable to represent
    show_defining_class: bool
        Show class that defined method instead of the name of class of object to
        which the method is bound.


    Returns
    -------
    str

    """

    if show_defining_class:
        cls = get_class_that_defined_method(func)
        kws['name_depth'] = 0
        return f'{cls.__name__}{caller(func, **kws)}'

    return caller(func, **kws)
