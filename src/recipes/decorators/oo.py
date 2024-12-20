

import types


class Singleton:
    # adapted from:
    # https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html

    def __init__(self, klass):
        self.klass = klass
        self.instance = None

    def __call__(self, *args, **kws):
        if self.instance is None:
            self.instance = self.klass(*args, **kws)
        return self.instance


# alias
singleton = Singleton


class sharedmethod(classmethod):  # adapted from astropy
    """
    This is a method decorator that allows both an instancemethod and a
    `classmethod` to share the same name.

    When using `sharedmethod` on a method defined in a class's body, it
    may be called on an instance, or on a class.  In the former case it
    behaves like a normal instance method (a reference to the instance is
    automatically passed as the first ``self`` argument of the method)::

        >>> class Example:
        ...     @sharedmethod
        ...     def identify(self, *args):
        ...         print('self was', self)
        ...         print('additional args were', args)
        ...
        >>> ex = Example()
        >>> ex.identify(1, 2)
        self was <astropy.utils.decorators.Example object at 0x...>
        additional args were (1, 2)

    In the latter case, when the `sharedmethod` is called directly from a
    class, it behaves like a `classmethod`::

        >>> Example.identify(3, 4)
        self was <class 'astropy.utils.decorators.Example'>
        additional args were (3, 4)

    This also supports a more advanced usage, where the `classmethod`
    implementation can be written separately.  If the class's *metaclass*
    has a method of the same name as the `sharedmethod`, the version on
    the metaclass is delegated to::

        >>> class ExampleMeta(type):
        ...     def identify(self):
        ...         print('this implements the {0}.identify '
        ...               'classmethod'.format(self.__name__))
        ...
        >>> class Example(metaclass=ExampleMeta):
        ...     @sharedmethod
        ...     def identify(self):
        ...         print('this implements the instancemethod')
        ...
        >>> Example().identify()
        this implements the instancemethod
        >>> Example.identify()
        this implements the Example.identify classmethod
    """

    def __get__(self, obj, objtype=None):
        if obj is not None:
            return self._make_method(self.__func__, obj)

        mcls = type(objtype)
        clsmeth = getattr(mcls, self.__func__.__name__, None)
        func = clsmeth if callable(clsmeth) else self.__func__
        return self._make_method(func, objtype)

    @staticmethod
    def _make_method(func, instance):
        return types.MethodType(func, instance)


# def all_methods(decorator, ignore=()):
#     """
#     A decorator that applies a given decorator to all methods in a class.
#     Useful for profiling / debugging.
#     """

#     def wrapper(cls):
#         if decorator:
#             for name, method in inspect.getmembers(
#                     cls, predicate=inspect.isfunction):
#                 # NOTE: For same reason, static methods don't like being
#                 #   decorated like this
#                 is_static = isinstance(
#                     cls.__dict__.get(name), staticmethod)
#                 if not (is_static or name in ignore):
#                     setattr(cls, name, decorator(method))
#         return cls

#     return wrapper
