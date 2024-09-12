
# std
import os
import itertools as itt
from collections import abc, defaultdict

# third-party
import more_itertools as mit

# relative
from ..string import indent


# ---------------------------------------------------------------------------- #
def pformat(mapping, name=None,
            lhs=None, equal=': ', rhs=None,
            sep=',', brackets='{}',
            align=None, hang=False,
            tabsize=4, newline=os.linesep,
            ignore=()):
    """
    Pretty format (nested) mappings.

    Parameters
    ----------
    mapping : MutableMapping
        Mapping to format as string.
    name : str, optional
        Name used in object representation. The object class name is used by
        default. In the case of `mapping` being a builtin `dict` instance, the
        name is set to an empty string in order to render them in a similar
        style to what the native repr produces.
    lhs : Callable or dict of callable, optional
        Function used to format dictionary keys, by default repr.
    equal : str, optional
        Symbol used for equal sign, by default ': '.
    rhs : Callable or dict of callable, optional
        Function used to format dictionary values, by default repr.
    sep : str, optional
        String used to separate successive key-value pairs, by default ','.
    brackets : str or Sequence of length 2, optional
        Characters used for enclosing brackets, by default '{}'.
    align : bool, optional
        Whether to align values (right hand side) in a column, by default True
        if `newline` contains an actual newline character '\\n', otherwise
        False.
    hang : bool, optional
        Whether to hang the first key-value pair on a new line, by default False.
    tabsize : int, optional
        Number of spaces to use for indentation, by default 4.
    newline : str, optional
        Newline character, by default os.linesep.
    ignore : tuple of str
        Keys that will be omitted in the representation of the mapping.

    Returns
    -------
    str
        Pretty representation of the dict.

    Examples
    --------
    >>> pformat(dict(x='hello',
                      longkey='w',
                        foo=dict(nested=1,
                                 what='?',
                                 x=dict(triple='nested'))))
    {'x':       'hello',
     'longkey': 'w',
     'foo':     {'nested': 1,
                 'what':   '?',
                 'x':      {'triple': 'nested'}}}

    Raises
    ------
    TypeError
        If the input `mapping` is not a MutableMapping instance.
    ValueError
        If incorrect number of `brackets` are given.
    """
    if not isinstance(mapping, abc.MutableMapping):
        raise TypeError(f'Object of type: {type(mapping)} is not a '
                        'MutableMapping')

    if name is None:
        name = ('' if (kls := type(mapping)) is dict else kls.__name__)

    brackets = brackets or ('', '')
    if len(brackets) != 2:
        raise ValueError(
            f'Brackets should be a pair of strings, not {brackets!r}.'
        )

    # set default align flag
    if align is None:
        align = os.linesep in newline

    # format
    string = _pformat(mapping,
                      # resolve formatting functions
                      _get_formatters(lhs), equal, _get_formatters(rhs),
                      sep, brackets,
                      align, hang,
                      tabsize, newline,
                      ignore)
    ispace = 0 if hang else len(name)
    string = indent(string, ispace)  # f'{" ": <{pre}}
    return f'{name}{string}' if name else string


def _get_formatters(fmt):
    # Check formatters are valid callables
    # Retruns
    # A defaultdict that returns `pformat` as the default formatter
    from recipes.pprint import pformat
    
    if fmt is None:
        fmt = pformat

    if callable(fmt):
        
        return defaultdict(lambda: fmt)

    if not isinstance(fmt, abc.MutableMapping):
        raise TypeError(
            f'Invalid formatter type {type(fmt)}. Key/value formatters should '
            f'be callable, or a mapping of callables.'
        )

    for key, func in fmt.items():
        if callable(func):
            continue

        raise TypeError(
            f'Invalid formatter type {type(fmt)} for key {key!r}. Key/value '
            f'formatters should be callable.'
        )

    # A defaultdict that returns `pformat` as the default formatter
    return defaultdict((lambda: pformat), fmt)


def _pformat(mapping, lhs_func_dict, equal, rhs_func_dict, sep, brackets,
             align, hang, tabsize, newline, ignore):

    if len(mapping) == 0:
        # empty dict
        return brackets

    # remove ignored keys
    if remove_keys := set(mapping.keys()) & set(ignore):
        mapping = mapping.copy()
        for key in remove_keys:
            mapping.pop(key)

    # note that keys may not be str, so first convert
    keys = tuple(lhs_func_dict[key](key) for key in mapping.keys())
    keys_size = list(map(len, keys))

    string, close = brackets
    pos = len(string)
    if align:
        # make sure we line up the values
        leqs = len(equal)
        width = max(keys_size)
        wspace = [width - w + leqs for w in keys_size]
    else:
        wspace = itt.repeat(1)

    if hang:
        string += newline
        close = newline + close
    else:
        tabsize = pos

    indents = mit.padded([hang * tabsize], tabsize)
    separators = itt.chain(
        itt.repeat(sep + newline, len(mapping) - 1),
        [close]
    )
    for pre, key, (okey, val), wspace, end in \
            zip(indents, keys, mapping.items(), wspace, separators):
        # THIS places ':' directly before value
        # string += f'{"": <{pre}}{key: <{width}s}{equal }'
        # WHILE this places it directly after key
        # print(f'{pre=:} {key=:} {width=:}')
        # print(repr(f'{"": <{pre}}{key}{equal: <{width}s}'))
        # new = f'{"": <{pre}}{key}{equal: <{width}s}'
        string += f'{"": <{pre}}{key}{equal: <{wspace}s}'

        if isinstance(val, abc.MutableMapping):
            part = _pformat(val, lhs_func_dict, equal, rhs_func_dict, sep,
                            brackets, align, hang, tabsize, newline, ignore)
        else:
            part = rhs_func_dict[okey](val)

        # objects with multi-line representations need to be indented
        # `post` is item sep or closing bracket
        string += f'{indent(part, tabsize + len(key) + wspace)}{end}'

    return string


class PrettyPrint:
    """Mixin class that pretty prints dictionary content."""

    def __str__(self):
        return pformat(self)  # self.__class__.__name__

    def __repr__(self):
        return pformat(self)  # self.__class__.__name__

    def pformat(self, **kws):
        return pformat(self, **kws)

    def pprint(self, **kws):
        print(self.pformat(**kws))


# alias
PPrinter = Pprinter = PrettyPrint
