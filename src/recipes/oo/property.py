
"""
Extensions for buitlin property decorator.
"""


# std
import threading
import operator as op
from collections import abc
from types import FunctionType

# third-party
from loguru import logger


# ---------------------------------------------------------------------------- #
_NotFound = object()


# ---------------------------------------------------------------------------- #

class ForwardProperty:
    """
    Forward nested property to a parent class.
    """

    def __init__(self, name):
        self.parent_name, self.property_name = str(name).split('.', 1)
        self._dependents = []

    def __get__(self, obj, kls=None):
        # sourcery skip: assign-if-exp, reintroduce-else
        # get parent object
        if obj is None:
            # lookup from class
            return self

        return op.attrgetter(self.property_name)(getattr(obj, self.parent_name))

    def __set__(self, obj, value):
        parent = getattr(obj, self.parent_name)
        setattr(parent, self.property_name, value)

    def __delete__(self, obj):
        parent = getattr(obj, self.parent_name)
        del parent


# class ForwardProperty:
#     """
#     Forward nested property to a parent class.
#     """

#     def __init__(self, parent, name):
#         self.parent = parent
#         self.property_name = str(name)

#     def __get__(self, instance, kls=None):
#         # sourcery skip: assign-if-exp, reintroduce-else
#         # get parent object
#         if instance is None:
#             # lookup from class
#             return self

#         # parent = getattr(instance, self.parent_name)
#         return op.attrgetter(self.parent)(self.property_name)

#     def __set__(self, instance, value):
#         # parent = getattr(instance, self.parent_name)
#         setattr(self.parent, self.property_name, value)


class ClassProperty(property):
    """
    Allows properties to be accessed from class or instance

    Examples
    --------

    >>> class Example:
    ...
    ...    _name = None  # optional name.
    ...    # Optional name. Defaults to class name if not over-written by 
    ...    # inheritors.
    ...
    ...    @ClassProperty
    ...    @classmethod
    ...    def name(cls):
    ...        return cls._name or cls.__name__
    ...
    ...    @name.setter
    ...    def name(self, name):
    ...        self.set_name(name)
    ...
    ...    @classmethod
    ...    def set_name(cls, name):
    ...        assert isinstance(name, str)
    ...        cls._name = name
    ...
    ... obj = Example()
    ... obj.name
    'Example'
    >>> obj.name = 'New'
    ... (obj.name, Example.name)
    ('New', 'New')

    NOTE:FIXME Class level assignment OVERWRITES `name` - doesn't go through
    setter
    >>> Example.name = 'zzz'
    ... obj.name, Example.name
    ('zzz', 'zzz')

    """

    def __get__(self, instance, kls):
        return self.fget.__get__(None, kls)()


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
        ...         print('Computing the value for complicated_property...')
        ...         return 42
        ...
        >>> lt = LazyTest()
        >>> lt.complicated_property
        Computing the value for complicated_property...
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
        Computing the value for complicated_property...
        1764
        >>> lt.dependent_property
        1764
        >>> del lt.complicated_property
        ... lt.dependent_property
        Computing the value for complicated_property...
        1764

    The snippet above shows that the child property will automatically be
    deleted the parent was deleted or changed.

    Since the caching mechanism implicitly assumes mutability of the property
    (the case where the user explicitly changes the value of the property by
    assigning to the target attribute), the `read_only` keyword argument can be
    used to create immutable CachedProperty instances. Any attempt to change the
    value of a read-only property will raise an `AttributeError`.

        >>> class LazyTest3:
        ...     @CachedProperty(read_only)
        ...     def complicated_property(self):
        ...         print('Computing the value for complicated_property...')
        ...         return 42
        ...
        >>> lt = LazyTest3()
        >>> lt.complicated_property
        Computing the value for complicated_property...
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
            # if isinstance(parent, property):
            #     parent.fset

            if not isinstance(parent, (CachedProperty, ForwardProperty)):
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
