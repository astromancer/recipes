"""
Some drop-in replacements for the cool builtin operator classes, but with added
support for default values 
"""

# pylint: disable=redefined-builtin
# pylint: disable=invalid-name

import warnings
from recipes.decor import raises
import docsplice as doc

import builtins
from operator import eq


class NULL:
    "Null singleton"


def any(itr, test=bool):
    """
    Return True if test(x) is True for any x in the iterable.
    If the iterable is empty, return False.

    This function performs exactly the same function as the builtin any, but 
    additionally allows the item evaluation test to be user-specified.

    Parameters
    ----------
    itr : iterable
        Items to be evaluated.
    test : callable, optional
        Test function for items in the iterable. Must return a bool. Default 
        is the builtin bool function.

    Returns
    -------
    bool

    Examples
    --------
    >>> any(('U', 'X'), str.isupper)
    True
    """
    return builtins.any(map(test, itr))


@doc.splice(any, replace={'any': 'all', 'False': 'True'})
def all(itr, test=bool):
    return builtins.all(map(test, itr))


def prepend(obj, prefix):
    return prefix + obj


def append(obj, suffix):
    return obj + suffix


class itemgetter:
    """
    Itemgetter
    """

    def __init__(self, *keys, default=KeyError, **defaults):
        self.keys = keys
        self.defaults = defaults
        typo = set(self.defaults.keys()) - set(self.keys)
        if typo:
            warnings.warn(f'Superfluous defaults: {typo}')
        self.default = default

        if default is KeyError:
            self.get_default = raises(KeyError)

    def __call__(self, obj):  # -> List:
        unpack = list if len(self.keys) > 1 else next
        return unpack(self.iter(obj))

    def get_default(self, key):
        # # pylint: disable=method-hidden
        return self.defaults.get(key, self.default)

    def iter(self, obj):
        for i in self.keys:
            try:
                yield obj[i]
            except (KeyError, IndexError):
                yield self.get_default(i)


# alias #
getitem = itemgetter


def index(obj, item, start=0, test=eq, default=NULL):
    """
    Find the index position of `item` in list `l`, or if a test function is
    provided, the first index position for which the test evaluates as true. If
    the item is not found, or no items test positive, return the provided
    default value.

    Parameters
    ----------
    obj : list or str
        The items to be searched
    item : object
        item to be found
    start : int, optional
        optional starting index for the search, by default 0
    test : callable, optional
        Function used to identify the item. Calling sequence of this function is
        `test(x, item)`, where `x` is an item from the input list. The function
        should return boolean value to indicate whether the position of that
        item is to be returned in the index list. The default is `op.eq`, which
        tests each item for equality with input `item`.
    default : object, optional
        The default to return if `item` was not found in the input list, by
        default None

    Returns
    -------
    int
        The index position where the first occurance of `item` is found, or
        where `test` evaluates true
    """
    # if not isinstance(l, list):
    #     l = list(l)

    test = test or eq
    for i, x in enumerate(obj[start:], start):
        if test(x, item):
            return i

    # behave like standard indexing by default
    #  -> only if default parameter was explicitly given do we return that
    #   instead of raising a ValueError
    if default is NULL:
        raise ValueError(f'{item} is not in {type(obj)}')

    return default
