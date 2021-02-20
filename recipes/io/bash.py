"""
Emulate bash brace expansion
"""
from collections import defaultdict
from pathlib import Path
import re

from recipes.lists import split_where


RGX_CURLY_BRACES = re.compile(r'(.*?)\{([^}]+)\}(.*)')


def brace_expand_iter(pattern):
    # handle special bash expansion syntax here  xx{12..15}.fits
    mo = RGX_CURLY_BRACES.match(pattern)
    if mo:
        folder = Path(pattern).parent
        head, middle, tail = mo.groups()
        if '..' in middle:
            start, stop = map(int, middle.split('..'))
            items = range(start, stop + 1)
            # bash expansion is inclusive of both numbers in brackets
        else:
            items = middle.split(',')

        for x in items:
            yield f'{head}{x}{tail}'


def brace_expand(pattern):
    return list(brace_expand_iter(pattern))


def brace_contract(items):
    """
    Inverse operation of bash brace expansion

    Parameters
    ----------
    items : [type]
        [description]

    Example
    -------


    Returns
    -------
    [type]
        [description]
    """

    # ensure list of strings
    items = sorted(map(str, items))

    if len(items) == 1:
        return items[0]

    head = shared_prefix(items)
    tail = shared_suffix(items)
    i0 = len(head)
    i1 = -len(tail) or None
    middle = [item[i0:i1] for item in items]

    try:
        nrs = list(map(int, middle))
    except ValueError:  # as err
        # not a numeric sequence
        fenced = middle
    else:
        # we have a number sequence! Split sequence into contiguous parts
        fenced = []
        enum = iter(nrs)
        # split where pointwise difference greater than 1. second argument in
        # api call below is ignored
        parts = split_where(nrs, '', 1, lambda x, _: x - next(enum) > 1)
        for seq in parts:
            fenced.append(_contract(seq))

    # todo: could recurse here ?
    # if len(fenced) > 1:
    #     brace_contract(fenced)

    # combine results
    brace = '{}' if len(fenced) > 1 else ('', '')
    middle = ",".join(fenced).join(brace)
    return f'{head}{middle}{tail}'


def _contract(seq):
    # [9, 10, 11, 12]  --> '{09..12}'
    n = len(seq)
    if n == 1:
        return seq[0]

    # zfill first, embrace: eg: {09..12} or {foo,bar}
    first, *_, last = seq
    sep = ',' if n == 2 else '..'
    return f'{{{first:>0{len(str(last))}}{sep}{last}}}'


def shared_prefix(items):
    common = ''
    for letters in zip(*items):
        if len(set(letters)) > 1:
            break
        common += letters[0]
    return common


def shared_suffix(items):
    return shared_prefix(map(reversed, items))[::-1]
