import os
import re
import inspect
import functools

from recipes.introspection import get_class_that_defined_method


def func2str(func, show_class=True, submodule_depth=1):
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
        if isinstance(func, functools.partial):
            func = func.func
            # represent missing arguments with unicode centre dot
            cdot = '·' #u'\u00B7'
            argstr = str(func.args).strip(')') + ', %s)' % cdot
            return 'partial(%s%s)' % (func2str(func.func), argstr)
        # just a plain function # FIXME: module???
        return func.__name__
    else:
        # a class method
        parents = cls.__module__.split('.')
        prefixes = parents[:-submodule_depth - 1:-1]
        parts = prefixes + [cls.__name__, func.__name__]
        return '.'.join(parts)


def get_module_name(filename, depth=1):
    name = inspect.getmodulename(filename)
    if name == '__init__':
        from pathlib import Path
        return filename[-depth-1:-1]

    return name.split('.', name.count('.') - depth)[-1]


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


def overlay(text, bgtext='', alignment='^', width=None):
    """overlay text on bgtext using given alignment."""

    # TODO: verbose alignment name conversions. see ansi.table.get_alignment

    if not (bgtext or width):  # nothing to align on
        return text

    if not bgtext:
        bgtext = ' ' * width  # align on clear background
    elif not width:
        width = len(bgtext)

    if len(bgtext) < len(text):  # pointless alignment
        return text

    # do alignment
    if alignment == '<':  # left aligned
        overlayed = text + bgtext[len(text):]
    elif alignment == '>':  # right aligned
        overlayed = bgtext[:-len(text)] + text
    elif alignment == '^':  # center aligned
        div, mod = divmod(len(text), 2)
        pl, ph = div, div + mod
        # start and end indeces of the text in the center of the bgtext
        idx = width // 2 - pl, width // 2 + ph
        overlayed = bgtext[:idx[0]] + text + bgtext[
                                             idx[1]:]  # center text on bgtext

    return overlayed


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


def seq_repr_trunc(seq, n=3):
    """"""
    if len(seq) > n:
        return '(%i ... %i)' % (seq[0], seq[-1])
    return repr(seq)