"""
Tricks with metaclasses
"""


def flaggerFactory(flag='_flagged', collection='_flagged'):
    """
    Factory for creating class-decorator pair for method flagging and collection

    Parameters
    ----------
    flag:
        name of attribute that ids decorated methods
    collection:
        name of attribute for the collection

    Returns
    -------
    FlaggedMixin        :       class
        The mixin class for handling collection of flagged methods
    flagger             :       function
        Decorator used for flagging

    Examples
    --------
    >>> # implicit alias declaration
    ... AliasManager, alias = flaggerFactory(collection='_aliases')
    ...
    ... class Child(AliasManager):
    ...     def __init__(self):
    ...         super().__init__()
    ...         for (alias,), method in self._aliases.items():
    ...             setattr(self, alias, method)
    ...
    ...     @alias('bar')
    ...     def foo(self):
    ...         '''foo doc'''
    ...         print('foo!')
    ...
    ... class GrandChild(Child): pass
    ... GrandChild().bar()  # prints 'foo!'

    """

    # ensure we have str for the attributes
    assert isinstance(flag, str)
    assert isinstance(collection, str)

    # **************************************************************************
    class MethodFlaggerMeta(type):
        """Metaclass to collect methods flagged with decorator"""

        def __new__(meta, name, bases, namespace, **kw):
            cls = super().__new__(meta, name, bases, namespace)

            # emulate inheritance for the flagged methods
            coll = {}
            for base in bases:
                coll.update(getattr(base, collection, {}))

            coll.update({getattr(method, flag): method.__name__
                         for _, method in namespace.items()
                         if hasattr(method, flag)})
            # NOTE: will only work for hashable args passed to flagger
            # set the collection attribute as a class variable
            setattr(cls, collection, coll)
            return cls

    # **************************************************************************
    class FlaggedMixin(metaclass=MethodFlaggerMeta):
        """
        Mixin that collects the flagged methods in a dict and assigns it to the
        %s attribute.
        """

        def __init__(self, *args, **kw):
            # bind the flagged methods to the instance
            # logging.debug('Collected these functions: %s', getattr(self, collection))

            flagged_methods = {
                name: getattr(self, method)
                for (name, method) in getattr(self, collection).items()}
            setattr(self, collection, flagged_methods)

    # TODO: use case without arguments
    def flagger(*args):
        """
        Decorator for flagging methods.  Methods decorated with this function
        will have the %s attribute set as whatever arguments are passed.
        The decorator will preserve docstrings etc., as it returns the original
        function.
        """

        # TODO: check if args hashable

        def decorator(func):
            setattr(func, flag, args)
            return func

        return decorator

    flagger.__doc__ = flagger.__doc__ % flag
    FlaggedMixin.__doc__ = FlaggedMixin.__doc__ % collection
    return FlaggedMixin, flagger


def altflaggerFactory(flag='_flagged', collection='_flagged'):
    """
    Factory for creating class-decorator pair for method flagging and collection.
    This implementation avoids using a metaclass (in some cases this plays better
    with multiple inheritance. (metaclass conflicts)).  However, it may not work
    if your class has properties that reference values set after initialization.
    It also does not support inheritance of flagged methods.

    Examples
    --------
    AliasManager, alias = altflaggerFactory(collection='aliases')
    class Foo( AliasManager ):
        def __init__(self):
            super().__init__()
            for method, alias in self.aliases:
                setattr( self, alias, method )
        @alias( 'bar' )
        def foo(*args):
            print( 'calling foo(',args,')' )
    Foo().bar()

    Notes
    -----
    When using multiple decorators for a given method, the flagger will need to
    be the outermost (top) one.
    """

    # ensure we have str for the attributes
    assert isinstance(flag, str)
    assert isinstance(collection, str)

    class FlaggedMixin(object):
        """
        Mixin that binds the flagged classmethods to an instance of the class
        """

        def __init__(self, *args, **kw):
            # collect the flagged methods via introspection
            _collection = {}
            for name in dir(self):
                method = getattr(self, name)
                if hasattr(method, flag):
                    # NOTE: will only work for hashable args passed to flagger
                    _collection[method] = getattr(method, flag)

            setattr(self, collection, _collection)

    def flagger(*args):
        """Decorator for flagging methods"""

        #
        def decorator(func):
            # adds an attribute to the decorated function with the name
            # passed in as `flag`
            setattr(func, flag, args)
            return func

        return decorator

    return FlaggedMixin, flagger
