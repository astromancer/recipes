
import hashlib


def array(a):
    #  NOTE: salted hash changes between different python processes so
    # >>> hash(a.data) # does not work

    # NOTE: this is fast enough for small arrays and *repeatable*
    return (a if (a is None or a is False)
            else hashlib.md5(a.tobytes()).hexdigest())
