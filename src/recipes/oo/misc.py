"""
Some object oriented code patterns.
"""


def coerce(obj, to, wrap, ignore=()):

    if isinstance(obj, ignore):
        return obj

    return to([obj] if isinstance(obj, wrap) else obj)


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
