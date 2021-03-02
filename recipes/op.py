"""
Some drop-in replacements for the cool builtin operator classes, but with added
support for default values 
"""

import warnings
from recipes.decor import raises
from operator import attrgetter

class itemgetter:
    def __init__(self, *keys, default=KeyError, **defaults):

        self.keys = tuple(map(str, keys))
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
