
# std
import itertools as itt
import contextlib as ctx
from pathlib import Path
from collections import abc, defaultdict

# relative
from ...iter import cofilter
from ...pprint.mapping import pformat


# ---------------------------------------------------------------------------- #
# utils

def is_dict(obj):
    return isinstance(obj, abc.MutableMapping)


# alias
isdict = is_mapping = is_map = is_dict


def dump(mapping, filename, **kws):
    """
    Write dict to file in human readable form

    Parameters
    ----------
    mapping : [type]
        [description]
    filename : [type]
        [description]
    """
    Path(filename).write_text(pformat(mapping, **kws))


def invert(d, conversion=None):
    if conversion is None:
        conversion = {list: tuple}

    inverted = type(d)()
    for key, val in d.items():
        kls = type(val)
        if kls in conversion:
            val = conversion[kls](val)

        if not isinstance(val, abc.Hashable):
            raise ValueError(
                f'Cannot invert dictionary with non-hashable item: {val} of '
                f'type {type(val)}. You may wish to pass a conversion mapping'
                ' to this function to aid invertingof mappings that contain '
                f'non-hashable items.'
            )

        inverted[val] = key
    return inverted


def groupby(func, items):
    """
    Group objects by function return value.

    Parameters
    ----------
    func : callable
        The group id function.
    items : Iterable
        Objects to be grouped.

    Examples
    --------
    >>> groupby(str.isupper, 'abcDEF')
    {False: ['a', 'b', 'c'], True: ['D', 'E', 'F']}

    Returns
    -------
    dict[Any, list]
        (group_id, items)
    """
    with ctx.suppress(TypeError):
        items = sorted(items, key=func)
    return {group: list(itr)
            for group, itr in itt.groupby(items, func)}


def merge(*mappings, **kws):
    """
    Merge an arbitrary number of dictionaries together by repeated update.

    Examples
    --------
    >>> merge(*({f'{(l := case(letter))}': ord(l)}
    ...        for case in (str.upper, str.lower) for letter in 'abc'),
    ...       z=100)
    {'A': 65, 'B': 66, 'C': 67, 'a': 97, 'b': 98, 'c': 99, 'z': 100}

    Returns
    -------
    dict
        Merged dictionary.
    """

    out = {}
    for mapping in mappings:
        out.update(mapping)
    out.update(kws)
    return out


def filter(func_or_mapping, mapping=None):
    func = func_or_mapping if mapping else None
    mapping = (mapping or func_or_mapping)
    new = zip(*cofilter(func, mapping.values(), mapping.keys())[::-1])

    if isinstance(mapping, defaultdict):
        return type(mapping)(mapping.default_factory, new)

    return type(mapping)(new)


def remove(mapping, keys, *extra):
    # remove keys
    split(mapping, keys, *extra)
    return mapping


def split(mapping, keys, *extra):
    if isinstance(keys, str):
        keys = keys,

    keys = (*keys, *extra)
    return mapping, dict(_split(mapping, keys))


def _split(mapping, keys):
    for key in keys:
        if key in mapping:
            yield key, mapping.pop(key)
