
"""
Extensions for buitlin property decorator.
"""


# std
import threading
from types import FunctionType

# third-party
from loguru import logger


class ForwardProperty:
    """
    Forward nested property to a parent class.
    """

    def __init__(self, name):
        self.parent_name = str(name).split('.', 1)
        self.property_name = str(name)

    def __get__(self, instance, kls=None):
        # sourcery skip: assign-if-exp, reintroduce-else
        # get parent object
        if instance is None:
            # lookup from class
            return self

        parent = getattr(instance, self.parent_name)
        return op.attrgetter(parent)(self.property_name)

    def __set__(self, instance, value):
        parent = getattr(instance, self.parent_name)
        setattr(parent, self.property_name, value)


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


# Extended from astropy.utils.decorators to add optional dependency on other
# lazy properties which will automatically delete the child if the parent was
# deleted

_NotFound = object()


class lazyproperty(property):

    def __new__(cls, maybe_func=None, *_, **__):
        obj = super().__new__(cls)

        if callable(maybe_func):
            cls.__init__(obj)
            return obj(maybe_func)

        return obj  # NOTE: `__init__` will be called when returning here

    def __init__(self, depends_on=(), *other_parents):
        # print('init', depends_on, other_parents)

        if isinstance(depends_on, FunctionType):
            # we end up here from line inside __call__:
            # super().__init__(fget, fset, fdel, doc)
            # Even though we should not?????!!!!!!!!!!
            return

        if depends_on:
            depends_on = (depends_on, *other_parents)

        self._depends_on = depends_on
        self._dependents = []
        # patch deletion for parent to also delete this property
        for parent in depends_on:
            if not isinstance(parent, lazyproperty):
                raise TypeError(
                    f'Parent object that this {(kls := self.__class__.__name__)} '
                    f'`depends_on` should also be a {kls} object, not '
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
