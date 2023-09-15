"""
Functional helpers.
"""


def noop(*_, **__):
    """Do nothing."""


def is_none(x):
    return x is None


def not_none(x):
    return x is not None


def echo0(_, *ignored_):
    """simply return the 0th parameter."""
    return _


def echo(*_):
    """Return all parameters unchanged."""
    return _


# ---------------------------------------------------------------------------- #
def negate(func=bool):
    """Negates a callable that returns boolean."""

    # TODO: double negate returns original
    def wrapped(obj):
        return not func(obj)

    return wrapped


# ---------------------------------------------------------------------------- #
def raises(kind):
    """Raises an exception of type `kind`."""

    assert issubclass(kind, BaseException)

    def _raises(msg):
        raise kind(msg)

    return _raises


# ---------------------------------------------------------------------------- #
class always:
    """A callable that always returns the same value."""

    def __init__(self, obj):
        self.obj = obj

    def __call__(self, func, *args, **kws):
        return self.obj

    def __str__(self):
        return f'{self.__class__.__name__}({self.obj})'

    __repr__ = __str__
