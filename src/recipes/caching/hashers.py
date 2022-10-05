
import hashlib


def array(a):

    if a is None:
        return

    # NOTE: this is fast enough for small arrays and *repeatable*
    return hashlib.md5(a.tobytes()).hexdigest()

    #  NOTE: salted hash changes between different python processes so
    # >>> hash(a.data) # does not work
