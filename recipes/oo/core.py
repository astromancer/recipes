"""
Some object oriented code patterns.
"""


class Singleton(object):
    class __Singleton:
        def __str__(self):
            return repr(self)

    instance = None

    def __init__(self):
        if Singleton.instance is None:
            Singleton.instance = Singleton.__Singleton()

    def __getattr__(self, name):
        return getattr(self.instance, name)


class ClassProperty(property):
    """
    Allows properties to be accessed from class or instance

    Examples
    --------

    class Foo(object):

        _name = None  # optional name.
         # Will default to class name if not over-written in inheritors

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
    >>> print(foo.name) # 'Foo'
    >>> foo.name = 'Yo'
    >>> print((foo.name, Foo.name)) # ('Yo', 'Yo')
    >>> Foo.name = 'zzz'
    >>> print(foo.name, Foo.name) # ('?', '?')

    """

    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class SelfAware(object):  # SelfAware
    """
    Implements a new instance from existing instance usage pattern

    Example:
        A = SelfAware
        A(A(A(1)))
    """
    _skip_init = False

    def __new__(cls, *args):
        if isinstance(args[0], cls):
            instance = args[0]
            instance._skip_init = True
            return instance
        else:
            return super().__new__(cls)

    def __init__(self, a):
        if self._skip_init:
            return
        else:
            self.a = a


if __name__ == '__main__':
    A = SelfAware
    A(A(A(1)))
