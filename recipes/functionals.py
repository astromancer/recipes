
def always_true(_):
    return True

def negate(func):
    def wrapped(obj):
        return not func(obj)
    return wrapped


def raises(kind):
    def _raises(msg):
        raise kind(msg)
    return _raises


def echo(_):
    return _


def echo0(key, *ignored_):
    return key

