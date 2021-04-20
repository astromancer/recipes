import textwrap as txw

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


def sub(string, mapping={}, **kws):  # sub / substitute
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
    >>> sub('option(A, B)', A='B', B'='A')
    'option(B, A)'
    >>> sub('AABBCC', A='B', B='C', C='c')
    'BBCCcc'
    >>> sub('hello world', h='m', o='ow', rld='', w='v')
    'mellow vow'

    Returns
    -------
    s: str

    """
    mapping = {**mapping, **kws}
    if not mapping:
        return string

    if len(mapping) == 1:
        # simple replace
        return string.replace(*next(iter(mapping.items())))

    dest = ''.join(mapping.values())  # FIXME: better problem detection!!!
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


def prepend(string, prefix):
    return prefix + string


def append(string, suffix):
    return string + suffix


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
    return _replace_affix(string, old_prefix, new_prefix, 0)


def replace_suffix(string, old_suffix, new_suffix):
    return _replace_affix(string, old_suffix, new_suffix, 1)


def shared_prefix(strings):
    common = ''
    for letters in zip(*strings):
        if len(set(letters)) > 1:
            break
        common += letters[0]
    return common


def shared_suffix(strings):
    return shared_prefix(map(reversed, strings))[::-1]


def shared_affix(strings):
    prefix = shared_prefix(strings)
    i0 = len(prefix)
    suffix = shared_suffix([item[:i0] for item in strings])
    return prefix, suffix


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
