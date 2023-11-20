
"""
Extensions for buitlin property decorator.
"""


# std
import threading
import operator as op
import functools as ftl
from collections import abc
from types import FunctionType

# third-party
from loguru import logger


# ---------------------------------------------------------------------------- #
_NotFound = object()


# ---------------------------------------------------------------------------- #
class PropertyForwarding:
    """
    Mixin class with method for forwarding property/attribute access to another
    object in it's namespace. Useful for exposing dynamic attributes of nested
    objects in the instance's namespace.
    """

    _property_forwarding = {}

    def __new__(cls, *args, **kws):
        # Attach property descriptors
        for member, attrs in cls._property_forwarding.items():
            for _ in attrs:
                setattr(cls, _, ForwardProperty(f'{member}.{_}'))

        return super().__new__(cls)

    # @classmethod
    # def forward_properties(cls, mapping: Dict[str, Collection[str]]):
    #     # Attach property descriptors
    #     for _ in attrs:
    #         setattr(cls, _, ForwardProperty(f'{member}.{_}'))


class ForwardProperty:
    """
    A descritor that forwards attribute/property lookup to another namespace
    member. Useful for exposing dynamic attributes of nested objects in the 
    parent namespace.
    
    This works like `op.attrgetter` but in addition allows setting attributes.
    """

    __slots__ = ('member', 'property_name', '_getter', '_dependents')

    def __init__(self, name):
        self.member, self.property_name = str(name).split('.', 1)
        self._getter = op.attrgetter(self.property_name)
        self._dependents = []

    def __get__(self, obj, kls=None):
        # sourcery skip: assign-if-exp, reintroduce-else
        # get parent object
        if obj is None:
            # lookup from class
            return self

        return self._getter(getattr(obj, self.member))

    def __set__(self, obj, value):
        member = getattr(obj, self.member)
        setattr(member, self.property_name, value)

    def __delete__(self, obj):
        member = getattr(obj, self.member)
        del member


# ---------------------------------------------------------------------------- #
# extended from astropy.utils.decorators.lazyproperty


class CachedProperty(property):
    """
    Works similarly to property(), but computes the value only once.

    This essentially memorizes the value of the property by storing the result
    of its computation in the ``__dict__`` of the object instance.  This is
    useful for computing the value of some property that should otherwise be
    invariant.  For example::

        >>> class LazyTest:
        ...     @CachedProperty
        ...     def complicated_property(self):
        ...         print('Computing the value of `complicated_property`.')
        ...         return 42
        ...
        >>> lt = LazyTest()
        >>> lt.complicated_property
        Computing the value for `complicated_property`.
        42
        >>> lt.complicated_property
        42

    As the example shows, the second time ``complicated_property`` is accessed,
    the ``print`` statement is not executed.  Only the return value from the
    first access off ``complicated_property`` is returned.

    By default, a setter and deleter are used which simply overwrite and
    delete, respectively, the value stored in ``__dict__``. Any user-specified
    setter or deleter is executed before executing these default actions.
    The one exception is that the default setter is not run if the user setter
    already sets the new value in ``__dict__`` and returns that value and the
    returned value is not ``None``.

    You may add optional dependencies on other CachedProperty instances, as
    follows (reusing the previous example):

        >>> class LazyTest2(LazyTest):
        ...     @CachedProperty(depends_on=LazyTest.complicated_property)
        ...     def dependent_property(self):
        ...         return self.complicated_property ** 2
        ...
        >>> lt = LazyTest2()
        >>> lt.dependent_property
        Computing the value of `complicated_property`.
        1764
        >>> lt.dependent_property
        1764
        >>> del lt.complicated_property
        ... lt.dependent_property
        Computing the value of `complicated_property`.
        1764

    The snippet above shows that the child property will automatically be
    deleted the parent was deleted or changed.

    Since the caching mechanism implicitly assumes mutability of the property
    (the case where the user explicitly changes the value of the property by
    assigning to the target attribute), the `read_only` keyword argument can be
    used to create immutable CachedProperty instances. Any attempt to change the
    value of a read-only property will raise an `AttributeError`.

        >>> class LazyTest3:
        ...     @CachedProperty(read_only=True)
        ...     def complicated_property(self):
        ...         print('Computing the value of `complicated_property`.')
        ...         return 42
        ...
        >>> lt = LazyTest3()
        >>> lt.complicated_property
        Computing the value of `complicated_property`.
        42
        >>> lt.complicated_property = 43
        AttributeError: This property is set to read only.

    """

    def __new__(cls, maybe_func=None, *funcs, **kws):
        obj = super().__new__(cls)

        if callable(maybe_func):
            cls.__init__(obj)
            return obj(maybe_func, *funcs)

        return obj  # NOTE: `__init__` will be called when returning here

    def __init__(self, *args, depends_on=(), read_only=False):
        # print('init', args, depends_on, read_only)

        if isinstance(depends_on, FunctionType):
            # we end up here from line inside __call__:
            # super().__init__(fget, fset, fdel, doc)
            # Even though we should not?????!!!!!!!!!!
            return

        #
        self.read_only = bool(read_only)

        # dependencies
        if not isinstance(depends_on, abc.Collection):
            depends_on = (depends_on, )

        self._depends_on = depends_on
        self._dependents = []
        # patch deletion for parent to also delete this property
        for i, parent in enumerate(depends_on):
            if not isinstance(parent, ALLOWED_DEPENDANT_TYPES):
                raise TypeError(
                    f'Dependency {f"{i} " if i else ""}of '
                    f'{(kls := self.__class__.__name__)} should also be a {kls}'
                    ', (or ForwardProperty) descriptor object, not '
                    f'{type(parent)}.')

            logger.debug('Adding dependent to parent {}', parent)
            parent._dependents.append(self)

    def __call__(self, fget, fset=None, fdel=None, doc=None):
        super().__init__(fget, fset, fdel, doc)
        self._key = self.fget.__name__
        self._lock = threading.RLock()
        return self

    def __get__(self, obj, owner=None):
        try:
            obj_dict = obj.__dict__
            val = obj_dict.get(self._key, _NotFound)
            if val is _NotFound:
                with self._lock:
                    # Check if another thread beat us to it.
                    val = obj_dict.get(self._key, _NotFound)
                    if val is _NotFound:
                        val = self.fget(obj)
                        obj_dict[self._key] = val
            return val
        except AttributeError:
            if obj is None:
                return self
            raise

    def __set__(self, obj, val):
        if self.read_only:
            raise AttributeError('This property is set to read only.')

        obj_dict = obj.__dict__
        if self.fset:
            ret = self.fset(obj, val)
            if ret is not None and obj_dict.get(self._key) is ret:
                # By returning the value set the setter signals that it
                # took over setting the value in obj.__dict__; this
                # mechanism allows it to override the input value
                return
        obj_dict[self._key] = val
        self._delete_dependents(obj)

    def setter(self, fset):  # : Callable[[Any, Any], None] -> property:
        if self.read_only:
            raise AttributeError('This property is set to read only.')

        return super().setter(fset)

    def __delete__(self, obj):
        if self.fdel:
            self.fdel(obj)
        obj.__dict__.pop(self._key, None)    # Delete if present
        self._delete_dependents(obj)

    def _delete_dependents(self, obj):
        # delete dependents
        for child in self._dependents:
            logger.debug('delete child {}', child)
            child.__delete__(obj)

ALLOWED_DEPENDANT_TYPES = (CachedProperty, ForwardProperty)

# aliases
cachedproperty = cached_property = lazyproperty = CachedProperty

# ---------------------------------------------------------------------------- #

# class ClassProperty(property):
#     """
#     Allows properties to be accessed from class or instance

#     Examples
#     --------

#     >>> class Example:
#     ...
#     ...    _name = None  # optional name.
#     ...    # Optional name. Defaults to class name if not over-written by
#     ...    # inheritors.
#     ...
#     ...    @ClassProperty
#     ...    @classmethod
#     ...    def name(cls):
#     ...        return cls._name or cls.__name__
#     ...
#     ...    @name.setter
#     ...    def name(self, name):
#     ...        self.set_name(name)
#     ...
#     ...    @classmethod
#     ...    def set_name(cls, name):
#     ...        cls._name = str(name)
#     ...
#     ... obj = Example()
#     ... obj.name
#     'Example'
#     >>> obj.name = 'New'
#     ... (obj.name, Example.name)
#     ('New', 'New')

#     FIXME Class level assignment OVERWRITES `name` - doesn't go through
#     setter
#     >>> Example.name = 'zzz'
#     ... obj.name, Example.name
#     ('zzz', 'zzz')

#     """

#     def __get__(self, instance, kls):
#         return self.fget.__get__(None, kls)()


# copied from astropy.utils.decorators.classproperty

# TODO: This can still be made to work for setters by implementing an
# accompanying metaclass that supports it; we just don't need that right this
# second

class ClassProperty(property):
    """
    Similar to `property`, but allows class-level properties.  That is,
    a property whose getter is like a `classmethod`.

    The wrapped method may explicitly use the `classmethod` decorator (which
    must become before this decorator), or the `classmethod` may be omitted
    (it is implicit through use of this decorator).

    .. note::

        classproperty only works for *read-only* properties.  It does not
        currently allow writeable/deletable properties, due to subtleties of how
        Python descriptors work.  In order to implement such properties on a class
        a metaclass for that class must be implemented.

    Parameters
    ----------
    fget : callable
        The function that computes the value of this property (in particular,
        the function when this is used as a decorator) a la `property`.

    doc : str, optional
        The docstring for the property--by default inherited from the getter
        function.

    lazy : bool, optional
        If True, caches the value returned by the first call to the getter
        function, so that it is only called once (used for lazy evaluation
        of an attribute).  This is analogous to `lazyproperty`.  The ``lazy``
        argument can also be used when `classproperty` is used as a decorator
        (see the third example below).  When used in the decorator syntax this
        *must* be passed in as a keyword argument.

    Examples
    --------

    ::

        >>> class Foo:
        ...     _bar_internal = 1
        ...     @classproperty
        ...     def bar(cls):
        ...         return cls._bar_internal + 1
        ...
        >>> Foo.bar
        2
        >>> foo_instance = Foo()
        >>> foo_instance.bar
        2
        >>> foo_instance._bar_internal = 2
        >>> foo_instance.bar  # Ignores instance attributes
        2

    As previously noted, a `classproperty` is limited to implementing
    read-only attributes::

        >>> class Foo:
        ...     _bar_internal = 1
        ...     @classproperty
        ...     def bar(cls):
        ...         return cls._bar_internal
        ...     @bar.setter
        ...     def bar(cls, value):
        ...         cls._bar_internal = value
        ...
        Traceback (most recent call last):
        ...
        NotImplementedError: classproperty can only be read-only; use a
        metaclass to implement modifiable class-level properties

    When the ``lazy`` option is used, the getter is only called once::

        >>> class Foo:
        ...     @classproperty(lazy=True)
        ...     def bar(cls):
        ...         print("Performing complicated calculation")
        ...         return 1
        ...
        >>> Foo.bar
        Performing complicated calculation
        1
        >>> Foo.bar
        1

    If a subclass inherits a lazy `classproperty` the property is still
    re-evaluated for the subclass::

        >>> class FooSub(Foo):
        ...     pass
        ...
        >>> FooSub.bar
        Performing complicated calculation
        1
        >>> FooSub.bar
        1
    """

    def __new__(cls, fget=None, doc=None, lazy=False):
        if fget is None:
            # Being used as a decorator--return a wrapper that implements
            # decorator syntax
            def wrapper(func):
                return cls(func, lazy=lazy)

            return wrapper

        return super().__new__(cls)

    def __init__(self, fget, doc=None, lazy=False):
        self._lazy = lazy
        if lazy:
            self._lock = threading.RLock()   # Protects _cache
            self._cache = {}
        fget = self._wrap_fget(fget)

        super().__init__(fget=fget, doc=doc)

        # There is a buglet in Python where self.__doc__ doesn't
        # get set properly on instances of property subclasses if
        # the doc argument was used rather than taking the docstring
        # from fget
        # Related Python issue: https://bugs.python.org/issue24766
        if doc is not None:
            self.__doc__ = doc

    def __get__(self, obj, objtype):
        if self._lazy:
            val = self._cache.get(objtype, _NotFound)
            if val is _NotFound:
                with self._lock:
                    # Check if another thread initialised before we locked.
                    val = self._cache.get(objtype, _NotFound)
                    if val is _NotFound:
                        val = self.fget.__wrapped__(objtype)
                        self._cache[objtype] = val
        else:
            # The base property.__get__ will just return self here;
            # instead we pass objtype through to the original wrapped
            # function (which takes the class as its sole argument)
            val = self.fget.__wrapped__(objtype)
        return val

    def getter(self, fget):
        return super().getter(self._wrap_fget(fget))

    def setter(self, fset):
        raise NotImplementedError(
            "classproperty can only be read-only; use a metaclass to "
            "implement modifiable class-level properties")

    def deleter(self, fdel):
        raise NotImplementedError(
            "classproperty can only be read-only; use a metaclass to "
            "implement modifiable class-level properties")

    @staticmethod
    def _wrap_fget(orig_fget):
        if isinstance(orig_fget, classmethod):
            orig_fget = orig_fget.__func__

        # Using stock functools.wraps instead of the fancier version
        # found later in this module, which is overkill for this purpose

        @ftl.wraps(orig_fget)
        def fget(obj):
            return orig_fget(obj.__class__)

        return fget


# alias
classproperty = ClassProperty

