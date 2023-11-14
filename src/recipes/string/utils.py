"""
Utilities for operations on strings
"""

# std
import operator as op

# third-party
import more_itertools as mit

# relative
from .. import op, string
from ..iter import where
from ..utils import _delete_immutable


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

    return ''.join(_delete_immutable(string, indices)) if indices else string


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

    string = str(string)
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
            tmp[key] = str(id(key))  # sourcery skip: remove-unnecessary-cast
            good.pop(key)

    inv = {val: mapping[key] for key, val in tmp.items()}
    return _rreplace(_rreplace(_rreplace(string, tmp), good), inv)


# alias
substitute = sub

# alias
substitute = sub


def _rreplace(string, mapping):
    """blind recursive replace"""
    for old, new in dict(mapping).items():
        string = string.replace(old, new)
    return string


# ---------------------------------------------------------------------------- #
# Misc

def surround(string, left, right=None, sep=''):
    if not right:
        right = left
    return sep.join((left, string, right))


def indent(string, width=4):
    # indent `width` number of spaces
    return str(string).replace('\n', '\n' + ' ' * width)


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


# ---------------------------------------------------------------------------- #
# TODO:
# def uncomment(string, mark='#', keep=()):

#     re.compile(rf'(?s)((?![\\]).){mark}([^\n]*)')

# ---------------------------------------------------------------------------- #

def _partition_whitespace_indices(text):
    n = len(text)
    i0 = 0
    while i0 < n:
        i1 = next(string.where(text, op.ne, ' ', start=i0), n)
        yield (i0, i1)

        i2 = next(string.where(text, ' ', start=i1), n)
        yield (i1, i2)
        i0 = i2


def _split_whitespace(text):
    for i0, i1 in _partition_whitespace_indices(text):
        yield text[i0:i1]


def _partition_whitespace(text, min_length=5):
    buffer = ''
    for space, nonspace in mit.grouper(_split_whitespace(text), 2):
        if len(space) >= min_length:
            if buffer:
                yield buffer
            yield space
            buffer = nonspace
        else:
            if not buffer:
                yield ''

            buffer += space + nonspace

    yield buffer


def partition_whitespace(text, min_length=5):
    yield from mit.grouper(_partition_whitespace(text, min_length), 2)
