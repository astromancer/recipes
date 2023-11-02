"""
Tag and collect methods in your classes.
"""

# third-party
from loguru import logger

# relative
from ...decorators import Decorator
from ...logging import LoggingMixin


class MethodTaggerFactory:
    """
    Factory for method tagging decorator.
    """

    def __init__(self, tag: str):
        self.tag = tag

    def __call__(self, *info, **kws):
        return MethodTagger(self.tag, info, **kws)


class MethodTagger(Decorator, LoggingMixin):
    """
    Decorator for tagging methods. Methods decorated with this function will
    have the `{}` attribute set to the tuple of arguments passed to the
    decorator.

    This decorator will preserve function docstrings etc., since it returns the
    original function, only adding some attributes to it.
    """

    def __init__(self, tag, info):
        self.tag = str(tag)
        self.info = info
        # self.kws = kws
        self.__doc__ = MethodTagger.__doc__.format(tag)

    def __call__(self, func):
        # set the tag
        setattr(func, self.tag, self.info)
        self.logger.debug('Tagged {} with {!r}.', self.tag, self.info)
        # NOTE: kw tags (self.kws) ignored by default. Subclasses can use the
        # them by overwriting this method

        # Decorate the method. Even though the base implementation here wraps a
        # do-nothing decorator, subclasses can change functionality by
        # overwriting the `__wrapper__` method.
        return super().__call__(func)


class TagManagerMeta(type):
    """
    Constructor for classes that use method tags. 
    """

    # TODO: you can do this with a descriptor!

    _default_tag_name = '_tag'
    _default_collection_name = '_collected'

    _doc_template = __doc__ = """
        Mixin that collects the tagged methods in a dict and assigns it to the
        `{}` attribute.
        """

    # @classmethod
    # def __prepare__(cls, name, bases,
    #                 tag=_default_tag_name,
    #                 collection=_default_collection_name):
    #     return super().__prepare__(name, bases, tag=tag, collection=collection)

    # def resolve(self, which, kws):
    #     names = {}
    #     if (attr := kws.pop(which, None)):
    #         names[attr] = wrappers[which](attr)
    #         return names

    #     for base in bases:
    #         if isinstance(base, cls):
    #             names[which] = getattr(base, which)
    #             break
    #     else:
    #         raise TypeError(f'Could not find {which}.')

    def __new__(cls, name, bases, namespace,
                # tag='_tag', collection='_collected',
                **kws):

        if name == 'TagManagerBase':
            return super().__new__(cls, name, bases, namespace)

        # wrappers = dict(tag=MethodTaggerFactory,
        #                 collection=dict)
        # #
        # for which in ('tag', ):#'collection'):

        logger.debug('New class: {!r}', name)

        if (attr := kws.pop('tag', None)):
            namespace['tag'] = MethodTaggerFactory(attr)
        else:
            for base in bases:
                if isinstance(base, cls):
                    namespace['tag'] = getattr(base, 'tag')
                    break
            else:
                raise TypeError('Please supply a tag (str).')

        tagger = namespace['tag']
        tag = tagger.tag
        logger.debug('Found tag: {!r}.', tag)

        if (collection := kws.pop('collection', None)):
            namespace['_collection'] = collection
        else:
            for base in bases:
                if isinstance(base, cls):
                    namespace['_collection'] = collection = getattr(base, '_collection')
                    break
            else:
                raise TypeError('Please supply a collection name.')

        # set the collection attribute as a class variable
        namespace[collection] = collected = {}
        logger.debug('collection attribute is: {!r}', collection)

        # emulate inheritance for the tagged methods
        for base in bases:
            logger.debug('Updated collection for {!r} from base {}', name, base)
            collected.update(getattr(base, collection, {}))

        # collect
        collected.update({func.__name__: getattr(func, tag)
                          for _, func in namespace.items()
                          if hasattr(func, tag)})
        logger.debug('Collected the following tagged methods: {}', collected)

        # Create `TagManager` class
        return super().__new__(cls, name, bases, namespace)

    def _collect_tagged_methods(self, obj):
        # collect tagged (bound) methods of object
        return {
            getattr(obj, method_name): tag_info
            for (method_name, tag_info) in getattr(obj, self._collection).items()
        }


class TagManagerBase(metaclass=TagManagerMeta):
    """
    Mixin that collects the tagged methods in a dict and assigns it to the
    `{}` attribute.
    """

    # Note: this can't be implemented fully in TagCollectorMeta.__call__, since
    # that does not get called for ancestors of this class

    def __new__(cls, *args, **kws):
        # create object
        obj = super().__new__(cls)

        # collect (bound) methods to an instance attribute
        setattr(obj, cls._collection, cls._collect_tagged_methods(obj))

        # update the docstring
        if not obj.__doc__:
            obj.__doc__ = cls._doc_template.__doc__.format(cls._collection)

        return obj


def factory(tag='_tagged', collection='_collected'):
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
    ... AliasManagerBase, alias = factory(tag='_alias', collection='_aliases')
    ...
    ... class AliasManager(AliasManagerBase):
    ...     def __init__(self):
    ...         super().__init__() # collect tagged methods here
    ...         for method, (alias,) in self._aliases.items():
    ...             setattr(self, alias, method) # assign aliases
    ...
    ...     @alias('bar')
    ...     def foo(self):
    ...         '''This method is tagged: `_alias` attribute set to 'bar'.'''
    ...         print('foo!')
    ...
    ... class MySubClass(AliasManager): 
    ...     pass
    ...
    ... obj = MySubClass()
    ... obj._aliases
    {}
    obj.bar()
    'foo!'

    """

    # ensure we have str for the attributes
    assert isinstance(tag, str)
    assert isinstance(collection, str)

    # **************************************************************************

    class TagManager(TagManagerBase,
                     tag=tag, collection=collection):
        pass

    return TagManager, TagManager.tag


def alt_factory(tag='_tagged', collection='_collected'):
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

        def decorator(func):
            # adds an attribute to the decorated function with the name
            # passed in as `tag`
            setattr(func, tag, args)
            return func

        return decorator

    return TagCollector, tagger
