"""
Functional decorators and other miscellaneous functions
"""


def always(obj):
    def wrapped(*_):
        return obj
    return wrapped


def negate(func=bool):
    def wrapped(obj):
        return not func(obj)
    return wrapped


def raises(kind):
    def _raises(msg):
        raise kind(msg)
    return _raises


def echo0(key, *ignored_):
    """simply return the 0th parameter"""
    return key


def echo(*_):
    """Return all parameters unchanged"""
    return _
