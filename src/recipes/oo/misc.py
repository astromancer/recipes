"""
Some object oriented code patterns.
"""


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

class Singleton:
    class __Singleton:
        def __str__(self):
            return repr(self)

    instance = None

    def __init__(self):
        if Singleton.instance is None:
            Singleton.instance = Singleton.__Singleton()

    def __getattr__(self, name):
        return getattr(self.instance, name)


#
# Singleton/BorgSingleton.py
# Alex Martelli's 'Borg'

# class Borg:
#     _shared_state = {}
#
#     def __init__(self):
#         self.__dict__ = self._shared_state
#
#
# class Singleton(Borg):
#     def __init__(self, arg):
#         Borg.__init__(self)
#         self.val = arg
#
#     def __str__(self):
#         return self.val

# ---------------------------------------------------------------------------- #


class SelfAwareness(type):
    """SelfAware type class"""
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
    is returned

    Examples
    --------
    >>> class A(SelfAware): 
            def __init__(self, a): 
                self.a = a 

    >>> a = A(1)
    >>> a is A(A(A(a)))
    True
    """

# ---------------------------------------------------------------------------- #


class ClassProperty(property):
    """
    Allows properties to be accessed from class or instance

    Examples
    --------

    class Foo:

        _name = None  # optional name.
        # Optional name. Defaults to class name if not over-written by inheritors

        @ClassProperty
        @classmethod
        def name(cls):
            return cls._name or cls.__name__

        @name.setter
        def name(self, name):
            self.set_name(name)

        @classmethod
        def set_name(cls, name):
            assert isinstance(name, str)
            cls._name = name

    >>> foo = Foo()
    >>> foo.name
    'Foo'
    >>> foo.name = 'Yo'
    >>> (foo.name, Foo.name)
    ('Yo', 'Yo')
    >>> Foo.name = 'zzz' # FIXME: OVERWRITES `name` - doesn't go through setter
    >>> foo.name, Foo.name
    ('zzz', 'zzz')

    """

    def __get__(self, instance, kls):
        return self.fget.__get__(None, kls)()
