"""
Pluralization (experimental).
"""


# std
from collections import abc

# relative
from ..utils import ensure_list


# ---------------------------------------------------------------------------- #
_PLURAL_SUFFIX_MAP = {
    'a':
        (None, 'e'),
    # eg:   knife -> knives
    #       hoof -> hoovesxx
    'f':
        (-1, 'ves'),
    'fe':
        (-2, 'ves'),

    # eg:   nucleus -> nuclei;
    #       radius -> radii
    #       fungus -> fungi
    # EXCEPTIONS:
    # eg: genus -> genera
    #     opus -> opera
    ('eus', 'ius', 'us'):
        (-2, 'i'),

    # eg:   synopsis  -> synopses
    #       thesis -> theses
    'is':
        (-2, 'es'),
    # note: this fails for eg; necropolis which has plural
    # necropolises or necropoleis or necropoles or necropoli

    # eg: tableau -> tableaux
    'eau':
        (None, 'x'),

    # eg:   vortex - > vortices
    ('ex', 'ix'):
        (-2, 'ices'),

    # eg: phenomenon -> phenomena
    #     criterion ->  criteria
    ('on'):
        (-2, 'a'),

    # eg:   success -> successes,
    #       watch -> watches ...
    ('s', 'sh', 'ch', 'x', 'z'):
        (None, 'es'),

    # eg:   concerti -> concerto
    'to':
        (-1, 'i'),

    # eg:   cilium -> cilia
    'um':
        (-2, 'a'),

    # eg:   array -> arrays
    ('ay', 'ey'):
        (None, 's'),

    # eg:   agency -> agencies
    'y':
        (-1, 'ies')
}

PLURALIA_TANTUM = {
    # unchanging / context dependent
    'aircraft',
    'bison',
    'deer',
    'fish',       # or fishes when refering to species of fishes
    'faux pas',
    'moose',
    'offspring',
    'grouse',
    'salmon',
    'series',
    'sheep',
    'shrimp',
    'software',
    'species',
    'swine',
    'trout',
    'tuna'
}


# ---------------------------------------------------------------------------- #

def naive_english_plural(word):

    if word in PLURALIA_TANTUM:
        return word

    return next(
        (
            f'{word[:n]}{suffix}'
            for end, (n, suffix) in _PLURAL_SUFFIX_MAP.items()
            if word.endswith(end)
        ),
        # everything else
        f'{word}s',
    )


def pluralise(text, items=(()), plural=None, n=None):
    """Conditional plural of `text` based on size of `items`."""

    return ((plural or naive_english_plural(text))
            if _is_plural(items, n)
            else text)


def _is_plural(items=(()), n=None):
    return _many(items) if n is None else n != 1


def _many(obj):
    return isinstance(obj, abc.Collection) and (len(obj) != 1)


# alias
pluralize = pluralise


def numbered(items, name, plural=None):
    return f'{len(items):d} {pluralise(name, items, plural):s}'


def named_items(items, name, plural=None, fmt=str, **kws):
    items = ensure_list(items)
    if not _many(items):
        return f'{name}: {fmt(next(iter(items)))}'

    from recipes import pprint

    return (f'{plural or naive_english_plural(name)}: '
            f'{pprint.collection(items, fmt=fmt)}')
