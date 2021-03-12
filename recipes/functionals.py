
def negate(func):
    def wrapped(obj):
        return not func(obj)
    return wrapped


def raises(kind):
    def _raises(msg):
        raise kind(msg)
    return _raises