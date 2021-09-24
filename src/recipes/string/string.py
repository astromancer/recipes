"""
Utilities for operations on strings
"""


# std
import re
import numbers
from collections import abc

# third-party
import numpy as np

# local
from recipes.iter import filter_duplicates


# regexes
REGEX_SPACE = re.compile(r'\s+')


class Percentage:
    """
    An object representing a percentage of something (usually a number) that
    computes the actual percentage value when called.
    """

    regex = re.compile(r'([\d.,]+)\s*%')

    def __init__(self, s):
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
        ValueError [description]
        """
        mo = self.regex.search(s)
        if mo:
            self.frac = float(mo.group(1)) / 100
        else:
            raise ValueError(
                f'Could not find a percentage value in the string {s!r}'
            )

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
        multiplies the parsed fraction with the number `total`

        Parameters
        ----------
        total : number, array-like
            Any number

        """
        self(total)

# ---------------------------------------------------------------------------- #
# Helpers / Convenience


def strings(items):
    """Map collection to list of str"""
    return [*map(str, items)]


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
    n = len(string)
    z = bytearray(string.encode())
    # remove duplicate indices accounting for wrapping
    indices = filter_duplicates(indices, lambda i: (i + n) % n)
    for i in sorted(indices, key=abs, reverse=True):
        del z[i]
    return z.decode()


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
    from recipes import op

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
    return text + ('s', 'es')[text.endswith('s')]


def plural(text, collection=(())):
    """conditional plural"""
    many = isinstance(collection, abc.Collection) and len(collection) != 1
    return naive_plural(text) if many else text


def numbered(collection, name):
    return '{:d} {:s}'.format(len(collection), plural(name, collection))


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
# def decomment(string, mark='#', keep=()):

#     re.compile(rf'(?s)((?![\\]).){mark}([^\n]*)')


def overlay(text, background='', alignment='^', width=None):
    """overlay text on background using given alignment."""

    # TODO: verbose alignment name conversions. see motley.table.get_alignment

    if not (background or width):  # nothing to align on
        return text

    if not background:
        background = ' ' * width  # align on clear background
    elif not width:
        width = len(background)

    if len(background) < len(text):  # pointless alignment
        return text

    # do alignment
    if alignment == '<':  # left aligned
        overlaid = text + background[len(text):]
    elif alignment == '>':  # right aligned
        overlaid = background[:-len(text)] + text
    elif alignment == '^':  # center aligned
        div, mod = divmod(len(text), 2)
        pl, ph = div, div + mod
        # start and end indeces of the text in the center of the background
        idx = width // 2 - pl, width // 2 + ph
        # center text on background
        overlaid = background[:idx[0]] + text + background[idx[1]:]
    else:
        raise ValueError('Alignment character %r not understood' % alignment)
    return overlaid


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
