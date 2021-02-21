import os
import re
import numbers

import numpy as np


# regexes
REGEX_SPACE = re.compile(r'\s+')


class Percentage(object):

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


        Raises
        ------
        ValueError [description]
        """
        mo = self.regex.search(s)
        if mo:
            self.frac = float(mo.group(1)) / 100
        else:
            raise ValueError(
                f'Could not find a percentage value in the string {s!r}')

    def __repr__(self):
        return f'Percentage({self.frac:.2%})'

    def __str__(self):
        return f'{self.frac:.2%}'

    def of(self, total):
        """
        Get the number representing by the percentage as a total. Basically just
        multiplies the parsed fraction with the number `total`

        Parameters
        ----------
        total : number, array-like
            Any number

        """
        if isinstance(total, (numbers.Real, np.ndarray)):
            return self.frac * total

        try:
            return self.frac * np.asanyarray(total, float)
        except ValueError:
            raise TypeError('Not a valid number or numeric array') from None


def match_brackets(string, brackets='()', return_index=True, must_close=False):
    """
    Find a matching pair of closed brackets in the string `s` and return the
    encolsed string as well as, optionally, the indices of the bracket pair.

    Will return only the first closed pair if the input string `s` contains
    multiple closed bracket pairs.

    If there are nested bracket inside `string`, only the outermost pair will be
    matched.

    If `string` does not contain the opening bracket, None is always returned

    If `string` does not contain a closing bracket the return value will be
    `None`, unless `must_close` has been set in which case a ValueError is
    raised.

    Parameters
    ----------
    string: str
        The string to parse
    brackets: str, tuple, list
        Characters for opening and closing bracket, by default '()'. Must have
        length of 2
    return_index: bool
        return the indices where the brackets where found
    must_close: int
        Controls behaviour on unmatched bracket pairs. If 1 or True a ValueError
        will be raised, if 0 or False `None` will be returned even if there is
        an opening bracket.  If -1, partial matches are allowed and the partial
        string beginning one character after the opening bracket will be
        returned. In this case, if `return_index` is True, the index of the
        closing brace position will take the value None.

    Example
    -------
    >>> s = 'def sample(args=(), **kws):'
    >>> r, (i, j) = match_brackets(s)
    ('args=(), **kws' , (10, 25))
    >>> r == s[i+1:j]
    True

    Returns
    -------
    match: str or None
        The enclosed str
    index: tuple or None
        (start, end) indices of the actual brackets that were matched

    Raises
    ------
    ValueError if `must_close` is True and there is no matched closing bracket

    """

    null_result = None
    if return_index:
        null_result = (None, (None, None))

    left, right = brackets
    if left not in string:
        return null_result

    # if right not in string:
    #     return null_result

    # 'hello(world)()'
    pre, match = string.split(left, 1)
    # 'hello', 'world)()'
    open_ = 1  # current number of open brackets
    for i, m in enumerate(match):
        if m in brackets:
            open_ += (1, -1)[m == right]
        if not open_:
            if return_index:
                p = len(pre)
                return match[:i], (p, p + i + 1)
            return match[:i]

    # land here if (outer) bracket unclosed
    if must_close == 1:
        raise ValueError(f'No closing bracket {right}')

    if must_close == -1:
        i = string.index(left)
        if return_index:
            return string[i + 1:], (i, None)
        return string[i + 1:]

    return null_result


def iter_brackets(string, brackets='()', return_index=True, must_close=False):
    """
    Iterate through consecutive (non-nested) closed bracket pairs.

    Parameters
    ----------
    string : [type]
        [description]
    brackets : str, optional
        [description], by default '()'
    return_index : bool, optional
        [description], by default True

    Yields
    -------
    [type]
        [description]
    """
    if return_index:
        def yields(sub, i, j):
            return sub, (i, j)
    else:
        def yields(sub, i, j):
            return sub

    while True:
        sub, (i, j) = match_brackets(string, brackets, True, must_close)
        if sub:
            yield yields(sub, i, j)
            string = string[j+1:]
        else:
            break


def unbracket(string, brackets='{}'):
    """
    Removes arbitrary number of enclosing brackets from string.
    Roughly equivalent to 
    >>> string.lstrip(brackets[0]).rstrip(brackets[1])
    except that only the brackets that are matching pairs will be removed.


    Parameters
    ----------
    s : str
        string to be stripped of brackets
    brackets : str, optional
        string of length 2 with opening and closing bracket pair,
        by default '{}'

    Example
    -------
    >>> unbracket('{{{{hello world}}}}')
    'hello world'

    Returns
    -------
    string
        The string with all enclosing brackets removed
    """
    inside, (i, j) = match_brackets(string, brackets, must_close=True)
    if (i == 0) and (j == len(string) - 1):
        return unbracket(inside)
    return string


def replace(string, mapping):
    """
    Replace all the sub-strings in `string` with the strings in `mapping`.
    Replacements are done simultaneously (as opposed to recursively).

    Parameters
    ----------
    s : str
        string on which mapping will take place
    mapping: dict
        sub-strings to replace

    Examples
    --------
    >>> replace('hello world', dict(hell='lo', wo='', r='ro', d='l'))
    'loo roll'
    >>> replace('option(A, B)', {'B': 'A', 'A': 'B'})
    'option(B, A)'

    Returns
    -------
    s: str

    """

    unique = set(mapping)
    ok = unique - set(mapping.values())
    trouble = unique - ok
    fix = {key: str(id(key)) for key in trouble}
    inv = {val: mapping[key] for key, val in fix.items()}
    good = {key: mapping[key] for key in ok}
    return _rreplace(_rreplace(_rreplace(string, good), fix), inv)


def _rreplace(string, mapping):
    """blind recursive replace"""
    for old, new in dict(mapping).items():
        string = string.replace(old, new)
    return string


def remove_suffix(string, suffix):
    # str.removesuffix python 3.9:
    if string.endswith(suffix):
        return string[:-len(suffix)]
    return string


def replace_suffix(string, old_suffix, new_suffix):
    if string.endswith(old_suffix):
        return string[:-len(old_suffix)] + new_suffix
    return string


def surround(string, wrappers):
    left, right = wrappers
    return left + string + right


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
    Produce strikethrough text using unicode modifiers

    Parameters
    ----------
    text : str
        Text to be struck trough

    Example
    -------
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

#     re.compile(rf'((?![\\]).){mark}([^\n]*)', re.S)


def banner(text, swoosh='=', width=80, title=None, align='^'):
    """

    Parameters
    ----------
    text
    swoosh
    width
    title
    align

    Returns
    -------

    """

    swoosh = swoosh * width
    if title is None:
        pre = swoosh
    else:
        pre = overlay(' ', swoosh, align)

    banner = os.linesep.join((pre, text, swoosh, ''))
    return banner


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

# idx = width//2-pl, width//2+ph                    #start and end indeces of the text in the center of the progress indicator
# s = fill*width
# return s[:idx[0]] + self + s[idx[1]:]                #center text
