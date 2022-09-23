"""
Some object oriented code patterns.
"""


def coerce(obj, to, wrap, ignore=()):
    if isinstance(obj, ignore):
        return obj
    return to([obj] if isinstance(obj, wrap) else obj)


def iter_subclasses(cls, _seen=None):
    """
    Generator over all subclasses of a given class, in depth first order.

    >>> list(iter_subclasses(int)) == [bool]
    True

    >>> class A: pass
    >>> class B(A): pass
    >>> class C(A): pass
    >>> class D(B,C): pass
    >>> class E(D): pass
    >>> list(iter_subclasses(A))
    [__main__.B, __main__.D, __main__.E, __main__.C]

    >>> # get ALL (new-style) classes currently defined
    >>> [cls.__name__ for cls in iter_subclasses] #doctest: +ELLIPSIS
    ['type', ... 'tuple', ...]
    """

    # recipe adapted from:
    # http://code.activestate.com/recipes/576949-find-all-subclasses-of-a-given-class/

    if not isinstance(cls, type):
        raise TypeError('iter_subclasses must be called with '
                        'new-style classes, not %.100r' % cls)
    if _seen is None:
        _seen = set()

    try:
        subs = cls.__subclasses__()
    except TypeError:  # fails only when cls is type
        subs = cls.__subclasses__(cls)

    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            yield from iter_subclasses(sub, _seen)


def list_subclasses(cls):
    return list(iter_subclasses(cls))

# ---------------------------------------------------------------------------- #


class SelfAwareness(type):
    """
    Meta class for SelfAware objects. When initializing a `SelfAware` class (by
    calling this metaclass) with an instance of the same class as the first
    parameter, that same instance is returned instead of initializing a new
    object. This allows an optimization for objects with heavy initialization
    overhead.
    """
    def __call__(cls, instance=None, *args, **kws):
        # this is here to handle initializing the object from an already
        # existing instance of the class
        if isinstance(instance, cls):
            return instance

        return super().__call__(instance, *args, **kws)


class SelfAware(metaclass=SelfAwareness):
    """"
    A class which is aware of members of its own class. When initializing with
    an already existing instance, `__init__` is skipped and the original object
    is returned.

    Examples
    --------
    >>> class A(SelfAware): 
    ...     def __init__(self, a): 
    ...         self.a = a
    ...
    ... a = A(1)
    ... a is A(A(A(a)))
    True
    """
    
# ---------------------------------------------------------------------------- #


class AttributeAutoComplete:
    """
    Attribute lookup that returns if the lookup key matches the start of the
    attribute name and the match is one-to-one. Raises AttributeError otherwise.

    Example
    >>> class SmartClass(AttributeAutoComplete):
    ...     some_long_attribute_name_that_is_overly_tautologous = '!'
    ... SmartClass().some
    '!'
    """

    def __getattr__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError as err:
            candidates = [_ for _ in self.__dict__ if _.startswith(key)]
            real, *others = candidates or (None, ())
            if others or not real:
                # ambiguous or non-existent
                raise err from None

            return super().__getattribute__(real)


# alias
AttributeAutocomplete = AttributeAutoComplete
