
# import builtins
# import math
import inspect
import functools as ftl
from ..introspect.utils import get_module_name
import textwrap as txw
# import types

from ..introspect import get_class_that_defined_method


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


def function(func, args=None, kws=None, wrap=80, show_modules=0,
             params_per_line=None, hang=None, show_defaults=True,
             value_formatter=repr):
    """
    Pretty format a function, and optionally, its paramater values
    """
    # todo ppl
    # TODO: option to not print param names
    # TODO: safety limit for large parameter values
    #           : safe_repr
    # TODO: update docstring
    # TODO: interject str formatter for types eg. np.ndarray?
    # TODO: colourise elements  / defaults / non-defaults

    if not callable(func):
        raise TypeError(f'Object {func} is not a callable')

    # get object name string with module
    name = '.'.join(
        filter(None, (get_module_name(func, show_modules),
                      func.__qualname__))
    )

    # format signature
    sig = signature(inspect.signature(func), args, kws,
                    wrap, show_modules, params_per_line,
                    hang, show_defaults, value_formatter)
    return name + sig.replace('\n', (' ' * len(name)) + '\n')


def signature(sig, args=(), kws=None, wrap=80, indent=1,
              params_per_line=None, hang=None, show_defaults=True,
              value_formatter=repr, pep570_marks=True):

    # format each parameter as 'param=value' pa
    if args or kws:
        # with_arg values provided
        ba = sig.bind(*args, **(kws or {}))
        if show_defaults:
            ba.apply_defaults()
        pars = ['='.join((p, value_formatter(val)))
                for p, val in ba.arguments.items()]
    else:
        # This prints the function signature with default values
        pars = sig.parameters
        if not show_defaults:
            pars = {name: par
                    for name, par in pars.items()
                    if par.default == par.empty}

        # format individual paramter value pairs
        pars, kinds = zip(*((parameter(p, value_formatter), p.kind)
                            for p in pars.values()))
        pars = list(pars)

        # inject special / and * markers PEP570
        if pep570_marks:
            if (POS in kinds) and (len(set(kinds)) > 1):
                # everything preceding / is position only
                pars.insert(kinds.index(POS) + 1, '/')

            if (KWO in kinds) and (VAR not in kinds):
                # everythin following * in keyword only
                pars.insert(kinds.index(KWO), '*')

    # format!
    if not pars:
        return '()'
 
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


def method(func, show_class=True, submodule_depth=1):
    """
    Get a nice string representing the function.

    Parameters
    ----------
    func: Callable
        The callable to represent
    show_class: bool
        whether to show the class name eg: 'MyClass.method'
    submodule_depth: int
        number of sub-module levels to show.
        eg: 'foo.sub.MyClass.method'  for depth of 2

    Returns
    -------
    str

    """

    if show_class:
        cls = get_class_that_defined_method(func)
    else:
        cls = None
        submodule_depth = 0

    if cls is None:
        # handle partial
        if isinstance(func, ftl.partial):
            func = func.func
            # represent missing arguments with unicode centre dot
            cdot = '·'  # u'\u00B7'
            argstr = str(func.args).strip(')') + ', %s)' % cdot
            return 'partial(%s%s)' % (method(func.func), argstr)
        # just a plain function # FIXME: module???
        return func.__name__
    else:
        # a class method
        # FIXME: this gives the wrong module.submodule structure if
        #  show_class=True
        parents = cls.__module__.split('.')
        prefixes = parents[:-submodule_depth - 1:-1]
        parts = prefixes + [cls.__name__, func.__name__]
        return '.'.join(parts)
