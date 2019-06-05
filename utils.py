import inspect


def decorateAll(decorator=None, exclude=()):
    """
    A decorator that applies a given decorator to all methods in a class.
    Useful for profiling / debugging.
    """

    def wrapper(cls):
        if decorator is not None:
            for name, method in inspect.getmembers(
                    cls, predicate=inspect.isfunction):
                # NOTE: For same reason, static methods don't like being
                #   decorated like this
                is_static = isinstance(
                        cls.__dict__.get(name, None), staticmethod)
                if not (is_static or name in exclude):
                    setattr(cls, name, decorator(method))
        return cls

    return wrapper

# import functools
#
# from .base import OptionalArgumentsDecorator

# class DecorateAll(OptionalArgumentsDecorator):
#     #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def __init__(self, cls, decorator, exclude=None):
#
#
#         self.decorator = decorator
#         self.exclude = [] if exclude is None else exclude
#
#     #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def __call__(self, *args, **kws):
#         return make_wrapper(*args, **kws)
#
#     #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def make_wrapper(self, cls):
#         @functools.wraps(cls)
#         def wrapper(*args, **kws):
#             for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
#                 if name not in self.exclude:
#                     setattr(cls, name, self.decorator(method))
#             return cls(*args, **kws)
#         return wrapper
