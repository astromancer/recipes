"""
Base classes for extensible decorators.
"""


# std
import contextlib as ctx

# third-party
from loguru import logger
from decorator import decorate



# ---------------------------------------------------------------------------- #
class Decorator:
    """
    Decorator class which supports optional initialization parameters. Can be
    pickled, unlike function based decorators / factory. The actual decorator
    should be implemented by overriding the `__wrapper__` method.

    There are two distinct use cases
    1) No explicit arguments provided to decorator.
    eg.:
    >>> @decorator
    ... def fun():
    ...     ...

    2) Explicit arguments and/or keywords provided to decorator.
    eg.:
    >>> @decorator('hello', foo='bar')
    ... def baz(*args, **kws): 
    ...     ...

    The function wrapper is created by running the `__call__` method of this
    class, which uses the `decorate` function from the `decorator` library under
    the hood. The actual decorator should be implemented by overriding
    `__wrapper__` method. The `__call__` method assigns the original function to
    the `__wrapped__` attribute of the `Decorator` instance, and updates the
    `__wrapper__` method to mimic the call signature and documentation of the
    original function by running `functools.update_wrapper`.

    Considering the usage patterns above:
    In the first case (no parameters to decorator), the wrapper will be built
    upon construction by running `__call__` (with the function `fun` as the only
    parameter) inside `__new__`. Initialization here is trivial.

    In the second use case, the `__init__` method should be implemented to
    handle the parameters ('hello', foo='bar') passed to the decorator
    constructor. As before, the `__call__` method creates the wrapper and
    returns the `__wrapper__` method as the new function.

    By default, this decorator does nothing besides call the original function. 
    Subclasses should implement the `__wrapper__` method to do the desired work.
    For example:
    >>> class increment(decorator):
    ...     def __wrapper__(self, *args, **kws)
    ...         return self.func(*args, **kws) + 1

    NOTE: The use case above is identified based on the type of object the
    constructor receives as the first argument. It is therefore impossible to
    use this decorator if the first argument to the initializer is intended to
    be some callable. This will not work as expected:

    >>> class CoerceTo(Decorator):
    ...     def __init__(self, new_type):
    ...         assert isinstance(new_type, type)
    ...         self.new_type = new_type
    ...
    ...     def __wrapper__(self, obj):
    ...         return super().__wrapped__(self.new_type(obj))
    ...
    ... @CoerceTo(str)    # NOPE!
    ... def buz(): 
    ...     ...

    This can be remedied by passing your callable to the initializer as a
    keyword parameter:
    >>> @CoerceTo(new_type=str)    # OK!
    ... def buz():
    ...     return ...
    ... buz()
    'Ellipsis'
    """

    # Purists might argue that this class is an anti-pattern since it invites
    # less explicit constructs that are confusing to the uninitiated.
    # Here it is. Use it. Don't use it. Up to you.

    __slots__ = '__wrapped__'

    def __new__(cls, maybe_func=None, *_, **__):
        # create class
        obj = super().__new__(cls)

        # Catch auto-init usage pattern
        if callable(maybe_func):
            # TODO check the annotations to see if callable expected

            # No arguments provided to decorator.
            # >>> @decorator
            # ... def foo(): ...
            cls.__init__(obj)
            return obj(maybe_func)  # create wrapper here

            # call => decorate / wrap the function
            # NOTE: init will *not* be called when returning here since we are
            # intentionally returning an object that is not an instance of this
            # class!

        # Explicit arguments and/or keywords provided to decorator.
        # >>> @decorator('hello world!')
        # ... def foo(): ...
        return obj  # NOTE: `__init__` will be called when returning here

    def __init__(self, *args, **kws):
        """
        Inherited classes can implement stuff here.
        """

    def __call__(self, func, kwsyntax=False):
        """
        Function wrapper created here.
        """
        assert callable(func)

        logger.debug('Decorating func: {}.', func)
        decorator = decorate(func, self.__wrapper__, kwsyntax=kwsyntax)
        # NOTE: this sets: __name__, __doc__, __wrapped__, __signature__,
        # __qualname_, [__defaults__, __kwdefaults__, __annotations___]
        # on the decorator.
        # NOTE: The function returned by decorate *is not the same object* as
        # `func` here!

        # func is instance attribute __wrapped__
        self.__wrapped__ = func
        # and func attribute __wrapper__ is instance
        with ctx.suppress(AttributeError):
            # This fails for methods
            func.__wrapper__ = decorator

        return decorator

    def __wrapper__(self, func, *args, **kws):
        """
        Default wrapper simply calls the original `__wrapped__` function.
        Subclasses should implement the actual decorator here.
        """
        # pylint: disable=no-self-use
        return func(*args, **kws)

    # def __reduce__(self):
    #     return self.__class__


# alias
decorator = Decorator


#
# def inclass(func):
#     return '.' in str(func)


# # NOTE: partial functions don't have the __name__, __module__ attributes!
# # retrieve the deepest func attribute -- the original func
# while isinstance(func, ftl.partial):
#     func = func.func
# self.__module__ = func.__module__
# self.__name__ = 'partial(%s)' % func.__name__


# class Wrapper:  # FunctionMimic
#     """
#     A picklable decorator. Does nothing by default.
#     """
#     def __new__(cls, func, wrapper):
#         if inclass(func):
#             # a method
#             return super().__new__(MethodWrapper)
#         return super().__new__(FunctionWrapper)

#     def __init__(self, func, wrapper):
#         assert callable(func)
#         assert callable(wrapper)
#         self.__wrapped__ = func
#         self.__wrapper__ = wrapper

#         # Update this class to look like the wrapped function
#         # ftl.update_wrapper(self, func)

#         # for decorated methods: make wrapped function MethodType to avoid
#         # errors downstream
#         # if inclass(func):
#         #     # FIXME: binds to the wrong class!!
#         #     #   at build time this function is still unbound!
#         #     func = types.MethodType(func, self)

#     def __repr__(self):
#         return f'<{type(self).__name__} for {self.__wrapped__.__qualname__!r}>'

#     def pformat(self, *args, **kws):
#         from .. import pprint as pp
#         return pp.caller(self.__wrapped__, *args, **kws)

#     def pprint(self, *args, **kws):
#         print(self.pformat(self.__wrapped__, *args, **kws))

#     def __reduce__(self):
#         print('REDUCE', self.__class__, self.__wrapped__, )
#         # return Decorator,
#         #return Wrapper, (self.__wrapped__, self.__wrapper__)
#         return Decorator(), (self.__wrapped__, )
#         # from IPython import embed
#         # embed(header="Embedded interpreter at 'src/recipes/decor/base.py':64")
#         # return echo, (self.__wrapped__, )

# def echo(obj):
#     return obj

# class FunctionWrapper(Wrapper):
#     def __call__(self, *args, **kws):
#         # Default null decorator
#         # print(self.__class__, 'calling', self.__wrapper__, args, kws)
#         return self.__wrapper__(*args, **kws)


# class MethodWrapper(Wrapper):
#     def __call__(self, *args, **kws):
#         # Default null decorator
#         # print(self.__class__, 'calling', self.__wrapper__, args, kws)
#         return self.__wrapper__(self.__wrapper__.__self__, *args, **kws)
