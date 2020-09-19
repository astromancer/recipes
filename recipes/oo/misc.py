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
    >>> a is A(A(A(a)))  # True
    """


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
    >>> print(foo.name, Foo.name) # ('zzz', 'zzz')

    """

    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()
