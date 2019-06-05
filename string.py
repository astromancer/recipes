import re


def resolve_percentage(val, total, as_int=True):
    """
    Convert a percentage str like '3%' to an integer fraction
    """
    if isinstance(val, str):
        if val.endswith('%'):
            frac = float(val.strip('%')) / 100
            # assert 0 < frac < 1
            n = frac * total
            if as_int:
                n = round(n)
            return n
        else:
            raise ValueError('Invalid percentage')
    return val


def rreplace(s, subs, repl):
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

    subs = list(subs)
    while len(subs):
        ch = subs.pop(0)
        s = s.replace(ch, repl)

    return s


# import numpy as np
# def wrap(s, wrappers):
#     if isinstance(wrappers, str):
#         return wrappers + s + wrappers
#     elif np.iterable(wrappers):
#         return s.join(wrappers)


def stripNonAscii(s):
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


def kill_brackets(line):
    pattern = '\s*\([\w\s]+\)'
    return re.sub(pattern, '', line)


def matchBrackets(s, brackets='()', return_index=True):
    """
    Find matching closed brackets.  Will return first closed pair if s contains
    multiple closed bracket pairs.

    Parameters
    ----------
    s
    brackets
    return_index: bool
        return the indices where the brackets where found

    Example
    -------
    >>> matchBrackets('def sample(args=(), **kws):')
    # 'args=(), **kws'

    Returns
    -------

    """

    left, right = brackets
    if left in s:
        pre, match = s.split(left, 1)
        open_ = 1
        for index in range(len(match)):
            if match[index] in brackets:
                open_ += [1, -1][int(match[index] == right)]
            if not open_:
                if return_index:
                    return match[:index], (len(pre), len(pre) + index + 1)
                return match[:index]

    if return_index:
        return None, None
