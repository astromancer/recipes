"""
Tag and collect methods in your classes.
"""

# third-party
from loguru import logger

# relative
from ...decorators import Decorator


# class MethodTaggerMeta(type):
#     def __new__(cls, tag):
#         # cls.tag
#         cls = super().__new__(cls, name, bases, namespace, **kws)


def factory(tag='_tagged', collection='_tagged'):
    """
    Factory for creating class-decorator pair for method tagging and collection.

    Parameters
    ----------
    tag: str
        Name of attribute that ids decorated methods.
    collection: str
        Name of the attribute where the collection will be stored.

    Returns
    -------
    TagCollector : class
        The mixin class for handling collection of tagged methods.
    tagger : function
        Decorator used for tagging.

    Examples
    --------
    >>> # implicit alias declaration
    ... AliasManager, alias = factory(collection='_aliases')
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
    ... class GrandChild(Child): 
    ...     pass
    ...
    ... GrandChild().bar()
    'foo!'

    """

    # ensure we have str for the attributes
    assert isinstance(tag, str)
    assert isinstance(collection, str)

    # **************************************************************************
    class MethodTagger(Decorator):
        """
        Decorator for tagging methods. Methods decorated with this function
        will have the `%s` attribute set as the tuple of arguments are passed.
        The decorator will preserve docstrings etc., as it returns the original
        function.
        """

        def __init__(self, *tag_info, **kws):
            self.tag_info = tag_info

        def __call__(self, func):
            # set the tag
            setattr(func, self.tag, self.tag_info)
            return func

    # TODO: use case without arguments
    MethodTagger.tag = tag
    MethodTagger.__doc__ = MethodTagger.__doc__ % tag

    # **************************************************************************
    class TagCollectorMeta(type):
        """Metaclass to collect methods tagged with decorator."""

        def __new__(cls, name, bases, namespace, **kws):
            cls = super().__new__(cls, name, bases, namespace)

            # emulate inheritance for the tagged methods
            collected = {}
            for base in bases:
                collected.update(getattr(base, collection, {}))

            # collect
            collected.update({func.__name__: getattr(func, tag)
                              for _, func in namespace.items()
                              if hasattr(func, tag)})
            logger.debug('Collected the following tagged methods: {}', collected)

            # set the collection attribute as a class variable
            setattr(cls, collection, collected)

            return cls

    class TagCollector(metaclass=TagCollectorMeta):
        """
        Mixin that collects the tagged methods in a dict and assigns it to the
        `%s` attribute.
        """
        # FIXME: can do this in TagCollectorMeta.__call__

        def __init__(self, *args, **kw):
            # bind the tagged methods to the instance
            tagged_methods = {
                getattr(self, method_name): tag_info
                for (method_name, tag_info) in getattr(self, collection).items()
            }

            setattr(self, collection, tagged_methods)

    TagCollector.__doc__ = TagCollector.__doc__ % collection
    return TagCollector, MethodTagger


def alt_factory(tag='_tagged', collection='_tagged'):
    """
    Factory for creating class-decorator pair for method tagging and collection.
    This implementation avoids using a metaclass (in some cases this plays better
    with multiple inheritance. (metaclass conflicts)).  However, it may not work
    if your class has properties that reference values set after initialization.
    It also does not support inheritance of tagged methods.

    Examples
    --------
    >>> AliasManager, alias = alt_factory(collection='aliases')
    ... class Foo(AliasManager):
    ...     def __init__(self):
    ...         super().__init__()
    ...         for method, alias in self.aliases:
    ...             setattr( self, alias, method )
    ...     @alias( 'bar' )
    ...     def foo(*args):
    ...         print( 'calling foo(',args,')' )
    ... Foo().bar()

    Notes
    -----
    When using multiple decorators for a given method, the tagger will need to
    be the outermost (top) one.
    """

    # ensure we have str for the attributes
    assert isinstance(tag, str)
    assert isinstance(collection, str)

    class TagCollector:
        """
        Mixin that binds the tagged methods to an instance of the class.
        """

        def __init__(self, *args, **kw):
            # collect the tagged methods via introspect
            _collection = {}
            for name in dir(self):
                method = getattr(self, name)
                if hasattr(method, tag):
                    _collection[method] = getattr(method, tag)

            setattr(self, collection, _collection)

    def tagger(*args):
        """Decorator for tagging methods"""

        #
        def decorator(func):
            # adds an attribute to the decorated function with the name
            # passed in as `tag`
            setattr(func, tag, args)
            return func

        return decorator

    return TagCollector, tagger
