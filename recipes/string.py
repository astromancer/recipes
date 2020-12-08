import re
import numbers

import numpy as np


class Percentage(object):

    regex = re.compile(r'([\d., ])%')

    def __init__(self, s):
        """
        Convert a percentage string like '3.23494%' to a floating point number
        and retrieve the actual number (of a total) that it represents

        Parameters
        ----------
        s : str
            The string representing the percentage, eg: '3%', '12.0001 %'

        Examples
        --------
        >>> Percentage('1.25%').of(12345)


        Raises
        ------
        ValueError
            [description]
        """
        mo = self.regex.search(s)
        if mo:
            self.frac = float(mo.group(1)) / 100
        else:
            raise ValueError(
                f'Could not interpret string {s!r} as a percentage')

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


def remove_brackets(line, brackets='()'):
    # TODO
    pattern = r'\s*\([\w\s]+\)'
    return re.sub(pattern, '', line)


# Brackets('[]').match('hello(world)')

def match_brackets(s, brackets='()', return_index=True, must_close=False):
    """
    Find a matching pair of closed brackets in the string `s` and return the
    encolsed string as well as, optionally, the indices or the bracket pair.

    Will return only the first closed pair if the input string `s` contains
    multiple closed bracket pairs.

    If there are nested bracket inside `s`, only the outermost pair will be
    matched. 

    If `s` does not contain the opening bracket, None is always returned

    If `s` does not contain a closing bracket the return value will be
    `None`, unless `must_close` has been set in which case a ValueError is
    raised.

    Parameters
    ----------
    s: str
        The string to parse
    brackets: str, tuple, list
        Characters for opening and closing bracket, by default '()'. Must have
        length of 2
    return_index: bool
        return the indices where the brackets where found
    must_close: bool
        Controls behaviour on unmatched bracket pairs. If True a ValueError will
        be raised, if False will return `None`

    Example
    -------
    >>> s = 'def sample(args=(), **kws):'
    >>> r, (i, j) = match_brackets(s)
    >>> r 
    'args=(), **kws'
    >>> i, j
    (10, 25)
    >>> r == s[i+1:j]
    True

    Returns
    -------
    match: str or None
        The enclosed str
    index: tuple or None
        (i, j) indices of the actual brackets that were matched

    Raises
    ------
        ValueError if `must_close` is True and there is no matched closing bracket

    """

    null_result = None
    if return_index:
        null_result = (None, (None, None))

    left, right = brackets
    if (left in s):
        if right not in s:
            if must_close:
                raise ValueError(f'No closing bracket {right}')
            return null_result

        # 'hello(world)()'
        pre, match = s.split(left, 1)
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

    if return_index:
        return None, (None, None)


def iter_brackets(s, brackets='()', return_index=True):
    while True:
        sub, (i, j) = match_brackets(s, brackets)
        if j:
            yield s[i+1:j], (i, j)
            s = s[j+1:]
        else:
            break


def rreplace(s, mapping):
    """
    Recursively replace all the characters / sub-strings in subs with the
    character / string in repl.

    Parameters
    ----------
    s :     characters / sub-strings to replace
        if str               - replace all characters in string with repl
        if sequence of str   - replace each string with repl

    subs
    repl

    Returns
    -------

    """

    for old, new in dict(mapping).items():
        s = s.replace(old, new)
    return s


# import numpy as np
# def wrap(s, wrappers):
#     if isinstance(wrappers, str):
#         return wrappers + s + wrappers
#     elif np.iterable(wrappers):
#         return s.join(wrappers)


def strip_non_ascii(s):
    return ''.join((x for x in s if ord(x) < 128))


# def centre(self, width, fill=' ' ):

# div, mod = divmod( len(self), 2 )
# if mod: #i.e. odd window length
# pl, ph = div, div+1
# else:  #even window len
# pl = ph = div

# idx = width//2-pl, width//2+ph                    #start and end indeces of the text in the center of the progress indicator
# s = fill*width
# return s[:idx[0]] + self + s[idx[1]:]                #center text
