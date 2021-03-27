"""
Some drop-in replacements for the cool builtin operator classes, but with added
support for default values 
"""

import warnings
from recipes.decor import raises
import docsplice as doc
from operator import attrgetter
import builtins


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
        return self.defaults.get(key, self.default)

    def iter(self, obj):
        for i in self.keys:
            try:
                yield obj[i]
            except (KeyError, IndexError):
                yield self.get_default(i)


# alias
getitem = itemgetter
