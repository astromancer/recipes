"""
Base class for extensible decorators.
"""

from loguru import logger
from decorator import decorate


# ---------------------------------------------------------------------------- #
class Wrapper:
    """
    Transparent wrapper for callables.
    """

    __slots__ = ('__wrapped__', '__wrapper__', '__factory__')

    def __init__(self, func, decorator=None, factory=None):
        self.__wrapped__ = func
        self.__wrapper__ = decorator
        self.__factory__ = factory or getattr(decorator, '__self__', None)

    def __repr__(self):
        from recipes.pprint import callers

        return (f'<{type(self).__name__}('
                f'{callers.describe(self.__wrapper__)}; '
                f'wraps: {callers.pformat(self.__wrapped__)})>')

    def __call__(self, *args, **kws):

        if self.__wrapper__:
            return self.__wrapper__(self.__wrapped__, *args, **kws)

        return self.__wrapped__(*args, **kws)

    def __reduce__(self):
        return self.__factory__, (self.__wrapped__, False)


class Factory:

    __wrapper_class__ = Wrapper

    def __init__(self, *args, **kws):
        """
        Inherited classes can initialize the factory here.
        """

    def __call__(self, func, wrapper, emulate=True, kwsyntax=False):
        """
        This is the decorator factory method, function wrapper is created here.

        Parameters
        ----------
        func : callable
            The callable to be wrapped.
        emulate : bool, optional
            If True, the default, Fully emulate the wrapped func so that the
            decorator object returned here appears nearly identical to the input
            func. If False, this method will return a `Wrapper` which makes
            explicit the distinction between the decorator and the wrapped
            function. This is often beneficial since explicit is better than 
            implicit.
        kwsyntax : bool, optional
            If True will place positional params in the args tuple even if they
            are called as keyword parameters user side. The default value is
            False.

        Returns
        -------
        FunctionType
            The decorator
        """
        assert callable(func)
        assert callable(wrapper)

        if emulate:
            # make the wrapper appear to be the original function. This should
            # confuse the noobs!
            logger.debug('Emmulating callable: {}.', func)
            decorator = decorate(func, wrapper, kwsyntax=kwsyntax)
            # NOTE: The function created here by decorate *is not the same
            # object* as the input `func`!
            # `decorate` sets: __name__, __doc__, __wrapped__, __signature__,
            # __qualname_, [__defaults__, __kwdefaults__, __annotations___]
            # on `decorator`.
            self.__wrapped__ = func

            # Set the wrapper attribute for symmetry with `Wrapper`
            decorator.__wrapper__ = wrapper
            # Link the factory
            decorator.__factory__ = self
            # should be the same as decorator.__wrapper__.__self__ if
            # emulate=False. If emulate=True, this factory cannot be reach
            # through introspection unless we refernce it here!
            return decorator

        # decorator is explicitly a Wrapper object!
        logger.debug('Initializing wrapper {} for: {}.',
                     self.__wrapper_class__.__name__, func)

        return self.__wrapper_class__(func, wrapper, self)


# ---------------------------------------------------------------------------- #

class Decorator(Factory):
    """
    A flexible decorator factory class which supports optional initialization
    parameters. Can be pickled, unlike function based decorators / factory. The
    actual decorator should be implemented by overriding the `__wrapper__`
    method.

    There are two distinct usage patterns currently supported:
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
    In the first case (no parameters to decorator), the wrapper will be created
    upon construction by running `__call__` (with the target callable as the
    first parameter) inside `__new__`. Initialization here is trivial.

    In the second use case, the `__init__` method should be implemented to
    handle the parameters ('hello', foo='bar') passed to the decorator
    constructor. As before, the `__call__` method creates the decorator.

    By default, this bass class implements decorators that do nothing besides
    call the original function. Subclasses should therefore implement the
    `__wrapper__` method to do the desired work. For example:

    >>> class traced(decorator):
    ...     # print function signatures before call.
    ...     def __wrapper__(self, func, *args, **kws):
    ...         parameters = (*args,
    ...                       *(map(" = ".join, *zip(*kws.items())) if kws else ()))
    ...         parameters = str(parameters.rstrip(', ')
    ...         print(f'Calling function: {func.__name__}{parameters}}.')
    ...         return func(*args, **kws)
    ...
    ... @traced
    ... def worker(a=1):
    ...     print('Now doing work.')
    ...
    ... worker(2)
    Calling function: worker(2).
    Now doing work.

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
            # call above creates the decorator
            # NOTE: __init__ will *not* be called hereafter like normal since we
            # are (intentionally) returning an object that is not an instance of
            # this class!

        # Explicit arguments and/or keywords provided to decorator.
        # >>> @decorator('hello world!')
        # ... def foo(): ...
        return obj  # NOTE: `__init__` will be called when returning here

    def __call__(self, func, emulate=True, kwsyntax=False):
        return super().__call__(func, self.__wrapper__, emulate, kwsyntax)

    def __wrapper__(self, func, *args, **kws):
        """
        Default wrapper simply calls the original `__wrapped__` function.
        Subclasses should implement the actual decorator here.
        """
        # pylint: disable=no-self-use
        return func(*args, **kws)


# alias
decorator = Decorator
