"""
Emulate bash brace expansion
"""
import itertools as itt
from collections import defaultdict
from pathlib import Path
import re
from recipes.string import iter_brackets, unbracket

from recipes.lists import split_where


RGX_CURLY_BRACES = re.compile(r'(.*?)\{([^}]+)\}(.*)')
RGX_BASH_RANGE = re.compile(r'(\d+)[.]{2}(\d+)')


# def brace_expand_iter(pattern):
#     # handle special bash expansion syntax here  xx{12..15}.fits
#     mo = RGX_CURLY_BRACES.match(pattern)
#     if mo:
#         # folder = Path(pattern).parent
#         head, middle, tail = mo.groups()
#         if '..' in middle:
#             start, stop = map(int, middle.split('..'))
#             items = range(start, stop + 1)
#             # bash expansion is inclusive of both numbers in brackets
#         else:

#             # items = middle.split(',')
#             # items = itt.chain.from_iterable(
#             #     map(brace_expand_iter, middle.split(',')))

#         for x in items:
#             # recurse here
#             # yield from brace_expand_iter(f'{head}{x}{tail}')
#             yield f'{head}{x}{tail}'
#     else:
#         yield pattern

def unclosed(string, open, close):
    return string.count(open) - string.count(close)


def splitter(string, brackets='{}', delimeter=','):
    # conditional splitter. split on delimeter only if its not enclosed by
    # brackets. need this for nested brace expansion a la bash
    merged = []
    part = None
    for part in string.split(delimeter):
        if unclosed(part, *brackets):
            merged.append(part)
            trial = delimeter.join(merged)
            if not unclosed(trial, *brackets):
                yield trial
                merged = []
        else:
            yield part


def brace_expand_iter(pattern, level=0):
    
    # FIXME:
    # ch{{1,2},{4..6}},main{1,2},{1,2}test
    # detect bad patterns like the one above and refuse
    
    # handle special bash expansion syntax here  xx{12..15}.fits
    inside = None
    for inside, (i, j) in iter_brackets(pattern, '{}'):
        head, tail = pattern[:i], pattern[j + 1:]
        # print(f'{inside=}', f'{tail=}')
        for part in _expander(inside, head, tail):
            yield from brace_expand_iter(part, level=level+1)

    if inside is None:
        yield pattern


def _expander(item, head='', tail=''):
    rng = RGX_BASH_RANGE.fullmatch(item)
    if rng:
        # bash expansion syntax implies an inclusive number interval
        items = range(int(rng[1]), int(rng[2]) + 1)    
    else:
        items = splitter(item)

    for x in items:
        yield f'{head}{x}{tail}'


def brace_expand(pattern):
    # >>> brace_expand('root/{search,these}/*.tex')
    # ['root/search/*.tex', 'root/these/*.tex']
    # >>> brace_expand('/**/*.{png,jpg}')
    # ['/**/*.png', '/**/*.jpg']

    return list(brace_expand_iter(pattern))


def brace_contract(items):
    # special cases
    if isinstance(items, str):
        items = [items]
        
    if len(items) == 1:
        # simply remove single items enclosed in brackets. NOTE this behaviour
        # is different from what bash does: it simply uses the name containing
        # {x} elements verbatim
        return unbracket(items[0], '{}', condition=lambda x: ',' not in x)
        
    # ensure list of strings
    items = sorted(map(str, items))

    # find prefixes / suffixes
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
