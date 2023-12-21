
import itertools as itt


# ---------------------------------------------------------------------------- #
# Super / subclass iterators

def subclasses(cls, _seen=None):
    """
    Generator over all subclasses of a given class, in depth first order.

    >>> list(subclasses(int)) == [bool]
    True

    >>> class A: pass
    >>> class B(A): pass
    >>> class C(A): pass
    >>> class D(B,C): pass
    >>> class E(D): pass
    >>> list(subclasses(A))
    [__main__.B, __main__.D, __main__.E, __main__.C]

    >>> # get ALL (new-style) classes currently defined
    >>> [cls.__name__ for cls in subclasses] #doctest: +ELLIPSIS
    ['type', ... 'tuple', ...]
    """

    # recipe adapted from:
    # http://code.activestate.com/recipes/576949-find-all-subclasses-of-a-given-class/

    if not isinstance(cls, type):
        from recipes.oo.repr_helpers import qualname
        raise TypeError(f'{qualname(subclasses)}` must be called with new-style'
                        f' classes, not {cls!r}.')

    _seen = _seen or set()
    for sub in cls.__subclasses__(*([cls] if (cls is type) else ())):
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            yield from subclasses(sub, _seen)


def superclasses(cls, _seen=None):

    if not isinstance(cls, type):
        raise TypeError('`iter.baseclasses` must be called with new-style '
                        'classes, not {cls!r}.')

    _seen = _seen or set()

    chain = []
    for base in cls.__bases__:
        if base not in _seen:
            _seen.add(base)
            yield base
            chain.append(superclasses(base, _seen))

    yield from itt.chain(*chain)


# alias
baseclasses = superclasses
