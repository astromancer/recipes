"""
Utilities for operations on strings
"""


# std

import re
import numbers
import warnings as wrn
import itertools as itt
from collections import abc

# third-party
import numpy as np
import more_itertools as mit

# relative
from .. import op
from ..iter import where
from ..misc import duplicate_if_scalar


# regexes
REGEX_SPACE = re.compile(r'\s+')

# justification
JUSTIFY_MAP = {'r': '>',
               'l': '<',
               'c': '^',
               's': ' '}


class Percentage:
    """
    An object representing a percentage of something (usually a number) that
    computes the actual percentage value when called.
    """

    regex = re.compile(r'([\d.,]+)\s*%')

    def __init__(self, string):
        """
        Convert a percentage string like '3.23494%' to a floating point number
        and retrieve the actual number (percentage of a total) that it
        represents

        Parameters
        ----------
        s : str The string representing the percentage, eg: '3%', '12.0001 %'

        Examples
        --------
        >>> Percentage('1.25%').of(12345)
        154.3125

        Raises
        ------
        ValueError
            If percentage could not be parsed from the string.
        """
        if mo := self.regex.search(string):
            self.frac = float(mo.group(1)) / 100
        else:
            raise ValueError(f'Could not find anything resembling a percentage'
                             f' in the string {string!r}.')

    def __repr__(self):
        return f'Percentage({self.frac:.2%})'

    def __str__(self):
        return f'{self.frac:.2%}'

    def __call__(self, number):
        try:
            if isinstance(number, numbers.Real):
                return self.frac * number

            if isinstance(number, abc.Collection):
                return self.frac * np.asanyarray(number, float)
        except ValueError:
            raise TypeError('Not a valid number or numeric array type.') \
                from None

    def of(self, total):
        """
        Get the number representing by the percentage as a total. Basically just
        multiplies the parsed fraction with the number `total`.

        Parameters
        ----------
        total : number, array-like
            Any number.

        Returns
        -------
        float or np.ndarray
        """
        return self(total)

# ---------------------------------------------------------------------------- #
# Helpers / Convenience


def strings(items):
    """Map collection to list of str"""
    return [*map(str, items)]


# ---------------------------------------------------------------------------- #
# String pattern matching

def similarity(a, b):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def most_similar(string, options, cutoff=0.5):
    from recipes.lists import cosort

    sims = [similarity(string, _) for _ in options]
    sims, options = cosort(sims, options, order=-1)
    # print('Similarities: {}', dict(zip(options, sims)))
    # sims = sorted(sims, reverse=True)

    potentials = where(sims, op.ge, cutoff)
    first = next(potentials, None)

    # at least one match above cutoff
    if first is None:
        return

    # and top two matches not equally similar
    second = next(potentials, None)
    if second and sims[first] == sims[second]:
        # ambiguous match
        return

    return options[first]


# ---------------------------------------------------------------------------- #
# Deletion / Substitution

def delete(string, indices=()):
    """
    Remove characters at position `indices` from string.

    Parameters
    ----------
    string : str
        The string from which to remove characters.
    indices : collection of int
        Character index positions to delete. Negative indices are supported. 
        Duplicated indices are filtered.

    Examples
    --------
    >>> delete('0123456789', [0, 9])
    '12345678'
    >>> delete('0123456789', [0, -1, 9])
    '12345678'
    >>> delete('0123456789', [0, -1])
    '12345678'

    Returns
    -------
    str
    """

    if not indices:
        return string

    return ''.join(_delete(string, indices))

# def _intervals_from_slices(slices, n):
#     from recipes.lists import cosort

#     intervals = zip(*cosort(*zip(s.indices(n) for s in slices)))
#     start, stop = next(intervals)
#     start, stop = [start], [stop]
#     for begin, end in intervals:
#         if begin < stop[-1]:
#             stop[-1] = end
#         else:
#             start.append(begin)
#             stop.append(end)
#     return start, stop


def _integers_from_slices(slices, n):
    integers = set()
    for s in slices:
        integers |= set(range(*s.indices(n)))
    return integers


def ensure_list(obj):
    if isinstance(obj, abc.Iterator):
        return list(obj)
    return duplicate_if_scalar(obj, 1, raises=False)


def _delete(string, indices):
    from recipes.dicts import groupby

    n = len(string)

    # ensure list
    indices = groupby(ensure_list(indices), type)
    integers = _integers_from_slices(indices.pop(slice, ()), n)
    for kls, idx in indices.items():
        if not issubclass(kls, numbers.Integral):
            raise TypeError(f'Invalid index type {kls}.')
        integers = integers.union(idx)

    # remove duplicate indices accounting for wrapping
    i = prev = -1
    for i in sorted({(i + n) % n for i in integers}):
        yield string[prev + 1:i]
        prev = i

    if i < n - 1:
        yield string[i + 1:]

    # BELOW ONLY WORKS FOR ASCII!!
    # z = bytearray(string.encode())
    # indices = filter_duplicates(indices, lambda i: (i + n) % n)
    # for i in sorted(indices, key=abs, reverse=True):
    #     del z[i]
    # return z#.decode()


def backspaced(string):
    """
    Resolve backspace control sequence "\b" by remove them and the characters
    that immediately preceed them. 

    Parameters
    ----------
    string : str

    Examples
    --------
    >>> backspaced('.?!\b\b')
    '.'
    """
    if '\b' not in string:
        return string

    return backspaced(delete(string, [i := string.index('\b'), max(i - 1, 0)]))


def insert(sub, string, index):
    """
    Insert a substring `sub` into `string` immediately before `index` position.

    Parameters
    ----------
    sub, string : str
        Any string.
    index : int
        Index position before which to insert `sub`. Index of 0 prepends, while
        -1 appends.


    Returns
    -------
    string
        Modified string
    """
    index = int(min((n := len(string), (index + n) % n)))
    return string[:index] + sub + string[index:]


def sub(string, mapping=(), **kws):
    """
    Replace all the sub-strings in `string` with the strings in `mapping`.

    Replacements are done simultaneously (as opposed to recursively), so that
    character permutations work as expected. See Examples below.

    Parameters
    ----------
    s : str
        string on which mapping will take place
    mapping: dict
        sub-strings to replace

    Examples
    --------
    # basic substitution (recursive replacement)
    >>> sub('hello world', {'h':'m', 'o ':'ow '})
    'mellow world'
    >>> sub('hello world', h ='m', o='ow', rld='')
    'mellow wow'
    >>> sub('hello world', {'h':'m', 'o ':'ow ', 'l':''})
    'meow word'
    >>> sub('hello world', hell='lo', wo='', r='ro', d='l')
    'loo roll'

    # character permutations
    >>> sub('option(A, B)', A='B', B='A')
    'option(B, A)'
    >>> sub('AABBCC', A='B', B='C', C='c')
    'BBCCcc'
    >>> sub('hello world', h='m', o='ow', rld='', w='v')
    'mellow vow'

    Returns
    -------
    s: str

    """

    mapping = {**dict(mapping), **kws}
    if not mapping:
        return string

    if len(mapping) == 1:
        # simple replace
        return string.replace(*next(iter(mapping.items())))

    # character permutations with str.translate are an efficient way of doing
    # single character permutations
    # if set(map(len, mapping.keys())) == {1}:
    #     return string.translate(str.maketrans(mapping))

    from recipes import cosort
    # from recipes import op

    # check if any keys are contained within another key. If this is true,
    # we have to substitute the latter before the former
    keys = set(mapping)
    okeys, ovals = cosort(
        *zip(*mapping.items()),
        key=lambda x: op.any(keys - {x}, op.contained(x).within)
    )
    good = dict(zip(okeys, ovals))
    tmp = {}
    for key in okeys:
        # if any values have the key in them, need to remap them temporarily
        if op.any(ovals, op.contained(key).within):
            tmp[key] = str(id(key))
            good.pop(key)

    inv = {val: mapping[key] for key, val in tmp.items()}
    return _rreplace(_rreplace(_rreplace(string, tmp), good), inv)


# alias
substitute = sub


def _rreplace(string, mapping):
    """blind recursive replace"""
    for old, new in dict(mapping).items():
        string = string.replace(old, new)
    return string


# ---------------------------------------------------------------------------- #
# Casing


def title(string, ignore=()):
    """
    Title case string with optional ignore patterns.

    Parameters
    ----------
    string : str
        sttring to convert to titlecase
    ignore : tuple of str
        These elements of the string will not be title cased
    """
    if isinstance(ignore, str):
        ignore = [ignore]

    ignore = [*map(str.strip, ignore)]
    subs = {f'{s.title()} ': f'{s} ' for s in ignore}
    return sub(string.title(), subs)


def snake_case(string):
    new, _ = re.subn('([A-Z])', r'_\1', string)
    return new.lstrip('_').lower()


def pascal_case(string):
    return string.replace('_', ' ').title().replace(' ', '')


def camel_case(string):
    string = pascal_case(string)
    return string[0].lower() + string[1:]

# ---------------------------------------------------------------------------- #
# Affixes


def remove_affix(string, prefix='', suffix=''):
    for i, affix in enumerate((prefix, suffix)):
        string = _replace_affix(string, affix, '', i)
    return string


def _replace_affix(string, affix, new, i):
    # handles prefix and suffix replace. (i==0: prefix, i==1: suffix)
    if affix and (string.startswith, string.endswith)[i](affix):
        w = (1, -1)[i]
        return ''.join((new, string[slice(*(w * len(affix), None)[::w])])[::w])
    return string


def remove_prefix(string, prefix):
    # str.removeprefix python 3.9:
    return remove_affix(string, prefix)


def remove_suffix(string, suffix):
    # str.removesuffix python 3.9:
    return remove_affix(string, '', suffix)


def replace_prefix(string, old, new):
    """
    Substitute a prefix string.

    Parameters
    ----------
    string : [type]
        [description]
    old : [type]
        [description]
    new : [type]
        [description]

    Examples
    --------
    >>> 

    Returns
    -------
    [type]
        [description]
    """
    return _replace_affix(string, old, new, 0)

# @doc.splice(replace_prefix)


def replace_suffix(string, old, new):
    return _replace_affix(string, old, new, 1)


def shared_prefix(strings, stops=''):
    common = ''
    for letters in zip(*strings):
        if len(set(letters)) > 1:
            break

        letter = letters[0]
        if letter in stops:
            break

        common += letter
    return common


def shared_suffix(strings, stops=''):
    return shared_prefix(map(reversed, strings), stops)[::-1]


def shared_affix(strings, pre_stops='', post_stops=''):
    prefix = shared_prefix(strings, pre_stops)
    i0 = len(prefix)
    suffix = shared_suffix([item[i0:] for item in strings], post_stops)
    return prefix, suffix

# ---------------------------------------------------------------------------- #
# pluralization (experimental)


def naive_plural(text):
    return text + ('e' * text.endswith('s')) + 's'


def plural(text, collection=(())):
    """conditional plural"""
    many = isinstance(collection, abc.Collection) and len(collection) != 1
    return naive_plural(text) if many else text


def numbered(collection, name):
    return f'{len(collection):d} {plural(name, collection):s}'


def named_items(name, collection, fmt=str):
    return f'{plural(name, collection)}: {fmt(collection)}'

# ---------------------------------------------------------------------------- #
# Misc


def surround(string, left, right=None, sep=''):
    if not right:
        right = left
    return sep.join((left, string, right))


def indent(string, width=4):
    # indent `width` number of spaces
    return string.replace('\n', '\n' + ' ' * width)


def truncate(string, size, dots=' … ', end=10):
    n = len(string)
    if n <= size:
        return string

    return f'{string[:(size - len(dots) - end)]}{dots}{string[-end:]}'

# ---------------------------------------------------------------------------- #
# Transformations


def strip_non_ascii(string):
    """
    Remove all non-ascii characters from a string.

    Parameters
    ----------
    string : str
        Text to be operated on

    Returns
    -------
    str
        Copy of original text with all non-ascii characters removed
    """
    return ''.join((x for x in string if ord(x) < 128))


def strike(text):
    """
    Produce strikethrough text using unicode modifiers.

    Parameters
    ----------
    text : str
        Text to be struck through

    Examples
    --------
    >>> strike('hello world')
    '̶h̶e̶l̶l̶o̶ ̶w̶o̶r̶l̶d'

    Returns
    -------
    str
        strikethrough text
    """
    return '\u0336'.join(text) + '\u0336'
    # return ''.join(t+chr(822) for t in text)


def monospaced(text):
    """
    Convert all contiguous whitespace into single space and strip leading and
    trailing spaces.

    Parameters
    ----------
    text : str
        Text to be re-spaced

    Returns
    -------
    str
        Copy of input string with all contiguous white space replaced with
        single space " ".
    """
    return REGEX_SPACE.sub(' ', text).strip()


# TODO:
# def uncomment(string, mark='#', keep=()):

#     re.compile(rf'(?s)((?![\\]).){mark}([^\n]*)')


def overlay(text, background='', align='^', width=None):
    """
    Overlay `text` on `background` using given `alignment`.

    Parameters
    ----------
    text : [type]
        [description]
    background : str, optional
        [description], by default ''
    align : str, optional
        [description], by default '^'
    width : [type], optional
        [description], by default None

    Examples
    --------
    >>> 

    Returns
    -------
    [type]
        [description]

    Raises
    ------
    ValueError
        [description]
    """
    # TODO: drop width arg
    # TODO: verbose alignment name conversions. see motley.table.get_alignment

    if not (background or width):  # nothing to align on
        return text

    if not background:
        background = ' ' * width  # align on clear background
    elif not width:
        width = len(background)

    if len(background) < len(text):  # pointless alignment
        return text

    # left aligned
    if align == '<':
        return text + background[len(text):]

    # right aligned
    if align == '>':
        return background[:-len(text)] + text

    # center aligned
    if align == '^':
        div, mod = divmod(len(text), 2)
        pl, ph = div, div + mod
        # start and end indeces of the text in the center of the background
        idx = width // 2 - pl, width // 2 + ph
        # center text on background
        return background[:idx[0]] + text + background[idx[1]:]

    raise ValueError(f'Alignment character {align!r} not understood')


# def centre(self, width, fill=' ' ):

# div, mod = divmod( len(self), 2 )
# if mod: #i.e. odd window length
# pl, ph = div, div+1
# else:  #even window len
# pl = ph = div

# idx = width//2-pl, width//2+ph
# #start and end indeces of the text in the center of the progress indicator
# s = fill*width

# return s[:idx[0]] + self + s[idx[1]:]                #center text


def resolve_justify(align):
    align = JUSTIFY_MAP.get(align.lower()[0], align)
    if align not in '<^> ':
        raise ValueError(f'Unrecognised alignment {align!r}')
    return align


def justify(text, align='<', width=None, length_func=len, formatter=str.format):
    """
    Justify a paragraph of text.

    Parameters
    ----------
    text : str
        Text to justify.
    align : str, optional
        Alignment, by default '<'.
    width : int, optional
        Line width. The default is None, which uses the terminal width if
        available, falling back to classic 80.

    Returns
    -------
    str
        Justified text.
    """
    return '\n'.join(_justify(text, align, width, length_func, formatter))


def _justify(text, align, width, length_func, formatter):

    align = resolve_justify(align)
    lines = text.splitlines()
    linewidths = list(map(length_func, lines))
    widest = max(linewidths)
    width = int(width or widest)
    if widest > width:
        wrn.warn(f'Requested paragraph width of {width} is less than the '
                 f'length of widest line: {widest}.')

    if align != ' ':
        for lw, line in zip(linewidths, lines):
            yield formatter('{: {}{}}', line, align, max(width, lw))
        return

    for w, line in zip(linewidths, lines):
        delta = width - w
        if delta < 0:
            yield line

        indices = list(where(line, ' '))
        d, r = divmod(delta, len(indices))
        for j, k in enumerate(indices[::-1]):
            yield insert(' ' * d + (j < r), line, k)


def width(string):
    """
    Find the width of a paragraph. Non-display chatacters are counted.

    Parameters
    ----------
    string : str
        A paragraph of text.


    Returns
    -------
    int
        Length of the longest line of text.
    """
    indices = [*where(string, '\n'), len(string)]

    if len(indices) == 1:
        return indices[0]

    return -min(map(op.sub, *zip(*mit.pairwise(indices))))


def _max_line_width(lines):
    return max(map(len, lines))


def hstack(strings, spacing=0, offsets=(), width_func=_max_line_width):
    """
    Stick two or more multi-line strings together horizontally.

    Parameters
    ----------
    strings
    spacing : int
        Number of horizontal spaces to be added as a column between the string
        blocks.
    offsets : Sequence of int
        Vertical offsets in number of rows between string blocks.


    Returns
    -------
    str
        Horizontally stacked string
    """

    # short circuit
    if isinstance(strings, str):
        return strings

    if len(strings) == 1:
        return str(strings[0])

    # get columns and trim trailing whitespace column
    columns = _get_hstack_columns(strings, spacing, offsets, width_func)
    columns = itt.islice(columns, 2 * len(strings) - 1)
    return '\n'.join(map(''.join, zip(*columns)))


def _get_hstack_columns(strings, spacing, offsets, width_func):

    # resolve offsets
    if isinstance(offsets, numbers.Integral):
        offsets = [0] + [offsets] * (len(strings) - 1)

    offsets = list(offsets)
    assert len(offsets) <= len(strings)

    # first we need to compute the widths
    widths = []
    lines_list = []
    max_length = 0
    for string, off in itt.zip_longest(strings, offsets, fillvalue=0):
        lines = str(string).splitlines()
        max_length = max(len(lines), max_length)
        widths.append(width_func(lines))   # ansi.length_seen(lines[0])
        lines_list.append(([''] * off) + lines)

    # Intersperse columns with whitespace
    for lines, width in zip(lines_list, widths):
        # fill whitespace
        yield mit.padded(lines, ' ' * (width), max_length)
        yield itt.repeat(' ' * spacing, max_length)


def vstack(strings,  justify_='<', width_=None, spacing=0):

    s = list(filter(lambda s: s is not None, strings))
    justify_ = duplicate_if_scalar(justify_, len(s))

    if width_ is None:
        width_ = max(map(width, s))

    vspace = '\n'.join(itt.repeat(' ' * width_, spacing))
    itr = itt.zip_longest(s, justify_, fillvalue=justify_)
    itr = (justify(par, just, width_) for par, just in itr)
    return '\n'.join(
        mit.interleave_longest(itr, itt.repeat(vspace, len(s) - 1))
    )
