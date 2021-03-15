import textwrap as txw
import inspect
import math
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

# brace - the python bracket ace
# from brace import

# Braces(string).iter / .tokenize / .parse / match / strip / split
# ( )
# Parentheses
# or
# round brackets


# { }
# Braces
# or
# curly brackets

# [ ]
# Brackets
# or
# square brackets

#
# ⟨ ⟩
# Chevrons
# or
# angle brackets

def match_brackets(string, brackets='()', return_index=True, must_close=False):
    """
    Find a matching pair of closed brackets in the string `s` and return the
    encolsed string as well as, optionally, the indices of the bracket pair.

    Will return only the first closed pair if the input string `s` contains
    multiple closed bracket pairs. To iterate over bracket pairs, use
    `iter_brackets`

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


def always_true(_):
    return True

# TODO: nested bracket iterator


class contained:
    def __init__(self, item):
        self.item = item

    def within(self, container):
        return self.item in container


def outermost(string, brackets, indices, nr):
    i, j = indices
    return remove_affix(string, *brackets) == string[i+1:j]


def get_test(condition):
    # function wrapper to support multiple call signatures for user defined
    # condition test
    npar = len(inspect.signature(condition).parameters)
    if npar == 4:
        return condition

    elif npar == 1:
        def test(string, brackets, indices, nr):
            i, j = indices
            return condition(string[i+1:j])
    else:
        raise ValueError('Condition test function has incorrect signature')

    return test


def iter_brackets(string, brackets='()', return_index=True, must_close=False,
                  condition=always_true):
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
        def yields(inside, i, j):
            return inside, (start + i, start + j)
    else:
        def yields(inside, i, j):
            return inside

    # get condition test call signature
    test = get_test(condition)

    start = 0
    nr = 0
    while True:
        inside, (i, j) = match_brackets(string, brackets, True, must_close)
        if inside is None:
            break

        # condition
        if test(string, brackets, (i, j), nr):
            yield yields(inside, i, j)

        # increment
        nr += 1
        start = j + 1
        string = string[start:]


# def _iter(string, brackets='()', return_index=True, must_close=False,
#                   condition=always_true, depth=math.inf, level=0):
#     """
#     Iterate through consecutive (non-nested) closed bracket pairs.

#     Parameters
#     ----------
#     string : [type]
#         [description]
#     brackets : str, optional
#         [description], by default '()'
#     return_index : bool, optional
#         [description], by default True

#     Yields
#     -------
#     [type]
#         [description]
#     """
#     if return_index:
#         def yields(inside, i, j):
#             return inside, (start + i, start + j)
#     else:
#         def yields(inside, i, j):
#             return inside

#     start = 0
#     while True:
#         inside, (i, j) = match_brackets(string, brackets, True, must_close)
#         if inside is None:
#             break

#         if condition(inside):
#           # THIS WILL UNPACK FROM THE INNERMOST OUTWARDS
#            yield from _iter(inside, )

#         start = j + 1
#         string = string[start:]


# def _iter_deep(string, brackets, return_index=True, must_close=False,
#                    condition=always_true, depth=math.inf, level=0):
#     # return if too deep
#     if level > depth:
#         return string

#     # inside, (i, j) = match_brackets(string, brackets, must_close=False)
#     # if inside is None or not condition(inside):
#     #     return string

#     tail = string[i:]
#     ran = False
#     for inside, (i, j) in iter_brackets(tail, brackets, return_index, must_close,
#                                         condition, level, level):
#         # THIS WILL UNPACK FROM THE INNERMOST OUTWARDS
#         yield from iter_brackets(inside, brackets, return_index, must_close,
#                                   condition, depth, level+1)
#         ran = True

#     if not ran:
#         yield inside


def unbracket(string, brackets='()', depth=math.inf, condition=always_true):
    """
    Removes arbitrary number of closed bracket pairs from a string up to
    requested depth.

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

    return _unbracket(string, brackets, get_test(condition), depth)


def _unbracket(string, brackets, test=always_true, depth=math.inf, level=0, nr=0):
    # return if too deep
    if level >= depth:
        return string

    # TODO:
    # itr = iter_brackets(tail, brackets, must_close=True, condition=test)
    # found = next(itr, None)
    # if found is None:
    #   return string

    inside, (i, j) = match_brackets(string, brackets)
    if (inside is None) or not test(string, brackets, (i, j), nr):
        return string

    # testing on sequence number for every element is probably less efficient
    # than slicing the iterator below. Can think of a good way of
    # implementing that? is there even use cases?

    out = string[:i]
    tail = string[i:]
    nr = -1
    itr = iter_brackets(tail, brackets, must_close=True, condition=test)
    for nr, (inside, (i, j)) in enumerate(itr):
        out += _unbracket(inside, brackets, test, depth, level+1, nr)

    # did the loop run?
    if nr == -1:
        out += inside

    return out + tail[j + 1:]


# #
#     itr = iter_brackets(string, brackets, condition=test)
#     try:
#         inside, (i, j) = next(itr)
#     except StopIteration:
#         return string
#     else:
#         out = string[:i]
#         tail = string[j + 1:]
#         nr = -1
#         for nr, (inside, _) in enumerate(itr):
#             out += _unbracket(inside, brackets, test, depth, level + 1, nr)

#         # did the loop run?
#         if nr > -1: # yes
#             return out + tail

#         # no? recurse on whatever is inside the brackets
#         return out + _unbracket(inside, brackets, test, depth, level + 1, nr) + tail


# # # alternatively
#     inside, (i, j) = match_brackets(string, brackets, must_close=False)
#     if inside is None or not test(inside, (i, j), nr):
#         return string

#     # testing on sequence number for every element is probably less efficient
#     # than slicing the iterator below. Can think of a good way of
#     # implementing that? is there even use cases?
#     # if condition is outermost:

#     out = string[:i]
#     tail = string[i:]
#     ran = False
#     itr = iter_brackets(tail, brackets, must_close=True, condition=test)
#     for nr, (inside, (i, j)) in enumerate(itr):
#         out += _unbracket(inside, brackets, test, depth, level+1, nr)
#         ran = True

#     if not ran:
#         out += inside

#     return out + tail[j + 1:]

# def to_fstring(string):
    #"'%s(xy=(%g, %g), ' % (self.__class__.__name__, *self.center)"
    # ---> 'self.__class__.__name__ + '(xy=(%g, %g), ' % self.center'


def sub(string, mapping):  # sub / substitute
    """
    Replace all the sub-strings in `string` with the strings in `mapping`.

    Replacements are done simultaneously (as opposed to recursively), so that
    character permutations work as expected. See Examples.

    Parameters
    ----------
    s : str
        string on which mapping will take place
    mapping: dict
        sub-strings to replace

    Examples
    --------
    # basic
    >>> sub('hello world', {'h':'m', 'o ':'ow '})
    'mellow world'
    >>> sub('hello world', dict(h ='m', o='ow', rld=''))
    'mellow wow'
    >>> sub('hello world', {'h':'m', 'o ':'ow ', 'l':''})
    'meow word'
    >>> sub('hello world', dict(hell='lo', wo='', r='ro', d='l'))
    'loo roll'
    # character permutations
    >>> sub('option(A, B)', {'B': 'A', 'A': 'B'})
    'option(B, A)'
    >>> sub('AABBCC', {'A':'B', 'B':'C', 'C':'c'}) 
    'BBCCcc'
    >>> sub('hello world', dict(h ='m', o='ow', rld='', w='v'))
    'mellow vow'

    Returns
    -------
    s: str

    """

    dest = ''.join(mapping.values())
    good = mapping.copy()
    tmp = {}
    for key in mapping.keys():
        if key in dest:
            tmp[key] = str(id(key))
            good.pop(key)

    inv = {val: mapping[key] for key, val in tmp.items()}
    return _rreplace(_rreplace(_rreplace(string, tmp), good), inv)

    # FIXME:
    #
    # replace(r"""\begin{equation}[Binary vector potential]
    # \label{eq:bin_pot_vec}
    # Ψ\qty(\vb{r}) = - \frac{GM_1}{\abs{\vb{r - r_1}}}
    #                 - \frac{GM_2}{\abs{\vb{r - r_2}}}
    #                 - ½{\qty(\vb{ω} \x \vb{r})}^2
    # \end{equation}""",
    #  {'_p': 'ₚ', 'eq:bin_pot_vec': 'eq:bin_pot_vec'} )

    # unique = set(mapping)
    # ok = unique - set(mapping.values())
    # trouble = unique - ok
    # tmp = {key: str(id(key)) for key in trouble}
    # inv = {val: mapping[key] for key, val in tmp.items()}
    # good = {key: mapping[key] for key in ok}
    # return _rreplace(_rreplace(_rreplace(string, tmp), good), inv)

# alias
substitute = sub 


def _rreplace(string, mapping):
    """blind recursive replace"""
    for old, new in dict(mapping).items():
        string = string.replace(old, new)
    return string


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
    


def remove_affix(string, prefix='', suffix=''):
    for i, affix in enumerate((prefix, suffix)):
        string = _replace_affix(string, affix, '', i)
    return string


def _replace_affix(string, affix, new, i):
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


def replace_prefix(string, old_prefix, new_prefix):
    return _replace_affix(string, old_suffix, new_suffix, 0)


def replace_suffix(string, old_suffix, new_suffix):
    return _replace_affix(string, old_suffix, new_suffix, 1)


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

#     re.compile(rf'(?s)((?![\\]).){mark}([^\n]*)')


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
