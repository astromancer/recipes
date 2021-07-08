"""
Multi-dimensional arrays with synchronized element access
"""


# std libs
import ctypes
import multiprocessing as mp
import multiprocessing.managers as mgr

# third-party libs
import numpy as np


# methods that need sync:
methods_to_sync = (
    '__repr__', '__str__', '__format__',

    '__getitem__', '__setitem__',

    '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__',

    '__contains__',
    '__bool__',

    '__add__', '__sub__', '__mul__', '__matmul__', '__truediv__',
    '__floordiv__',
    '__mod__', '__divmod__', '__pow__', '__lshift__', '__rshift__', '__and__',
    '__xor__', '__or__',

    '__radd__', '__rsub__', '__rmul__', '__rmatmul__', '__rtruediv__',
    '__rfloordiv__', '__rmod__', '__rdivmod__', '__rpow__', '__rlshift__',
    '__rrshift__', '__rand__', '__rxor__', '__ror__',

    '__iadd__', '__isub__', '__imul__', '__imatmul__', '__itruediv__',
    '__ifloordiv__', '__imod__', '__ipow__', '__ilshift__', '__irshift__',
    '__iand__', '__ixor__', '__ior__',

    '__neg__', '__pos__', '__abs__', '__invert__',

    # these for arrays with unit size
    '__complex__', '__int__', '__float__')

method_sync_template = """
def %s(self, *args):
    with self._shared:
        return np.ndarray.%s(self, *args)
"""


def init_synced_array(shape, fill_value=0, dtype=ctypes.c_double):
    global shared_array

    size = np.atleast_1d(shape).prod()
    base = mp.Array(dtype, size)
    base[:] = fill_value

    shared_array = np.ctypeslib.as_array(base.get_obj())
    shared_array = shared_array.reshape(shape)


class SyncedCounter:
    """
    synchronized shared-memory counter

    `mp.Value` values are locked by default. This is correct in the sense that
    even if an assignment consists of multiple operations (such as assigning
    a string which might be many characters) then this assignment is atomic.
    However, when incrementing a counter you'll still need an external lock,
    because incrementing loads the current value and then increments it and
    then assigns the result back to the Value.

    So without an external lock, you might run into the following circumstance:
        * Process 1 reads (atomically) the current value of the counter, then
          increments it
        * before Process 1 can assign the incremented counter back to the Value,
          a context switch occurrs
        * Process 2 reads (atomically) the current (unincremented) value of the
          counter, increments it, and assigns the incremented result (atomically)
          back to Value
        * Process 1 assigns its incremented value (atomically), blowing away the
          increment performed by Process 2

    source:
    https://eli.thegreenplace.net/2012/01/04/shared-counter-with-pythons-multiprocessing
    """

    def __init__(self, initval=0):
        self.val = mp.Value('i', initval)

    def __str__(self):
        return str(self.val.value)  # note sync here on attr access to `value`

    def __repr__(self):
        return str(self.val.value)

    def __mod__(self, val):
        return self.val.value % val

    def __iadd__(self, val):
        with self.val:  # lock
            raw_value = self.val.get_obj()  # gets underlying shared ctype mem
            raw_value.value = raw_value.value + val
            return self

    def __next__(self):
        return self.inc()

    def inc(self, val=1):
        with self.val:  # lock
            raw_value = self.val.get_obj()  # gets underlying shared ctype mem
            raw_value.value = raw_value.value + val
            return raw_value.value

    def get_value(self):
        return self.val.value  # this method already syncs

    def set_value(self, val):
        self.val.value = val  # this method already syncs

    def reset(self):
        self.set_value(0)


# class CounterProxy(BaseProxy):
#     _exposed_ = ['__next__', 'inc', 'get_value', 'set_value', 'reset']
#
#     def __next__(self):
#         return self._callmethod('__next__')


class SyncedArray(np.ndarray):
    """
    array subclass enabling synchronized parallel read/write access to shared
    memory with all the numpy fancy indexing niceties.
    """

    def __new__(cls, data=None, shape=None, fill=0,
                dtype=ctypes.c_double):

        # super signature
        # ndarray(shape, dtype=float, buffer=None, offset=0,
        #     strides=None, order=None)

        # Create the ndarray instance of our type, given the usual
        # ndarray input arguments.  This will call the standard
        # ndarray constructor, but return an object of our type.
        # It also triggers a call to NDArray.__array_finalize__
        # print( 'In __new__ with class %s' % cls)

        # TODO: move to func sync_array
        if data is None and shape is None:
            raise ValueError('Need either data or shape, or both')

        if data is not None:
            data = np.asanyarray(data).reshape(shape)
        else:
            data = np.full(shape, fill, np.dtype(dtype))

        shx = mp.Array(dtype, data.size)
        shx[:] = data.ravel()
        # NOTE mp.Array is a function that returns SynchronizedArray
        #  which syncs on access to `value` attribute as well as on
        #  `__getitem__`, `__setitem__`, `__getslice__`, `__setslice__`
        # TODO: may as well do all the syncing here since you are bypassing
        #  this object anyway!

        #  since we want ndarray advanced indexing methods, we use `RawArray`
        #  which simply wraps shared memory without any synchronization
        #  primitives and handle the syncs here

        # constructor
        obj = np.ndarray.__new__(cls, data.shape, dtype, buffer=shx.get_obj())

        # print('last bit of __new__ with class %s' % cls)
        obj._shared = shx

        # Finally, we must return the newly created object:
        return obj

    def __array_finalize__(self, obj):
        # print('In array_finalize:')
        # print('   self type is %s' % type(self))
        # print('   obj type is %s' % type(obj))
        #
        # print('have _shared self', hasattr(self, '_shared'))
        # print('have _shared obj', hasattr(obj, '_shared'))

        # ``self`` is a new object resulting from
        # ndarray.__new__(InfoArray, ...), therefore it only has
        # attributes that the ndarray.__new__ constructor gave it -
        # i.e. those of a standard ndarray.
        #
        # We could have got to the ndarray.__new__ call in 3 ways:
        # From an explicit constructor - e.g. InfoArray():
        #    obj is None
        #    (we're in the middle of the InfoArray.__new__
        #    constructor, and self.shared will be set when we return to
        #    InfoArray.__new__)
        if obj is None:
            return

        # print('Still In `__array_finalize__`')

        # we get here when one of the following happens:
        # 1) From view casting - e.g arr.view(SyncedArray):
        #    type(obj) is some `ndarray` subclass  - which can be SyncedArray
        #
        # We disallow view castings for SyncedArray
        if not hasattr(obj, '_shared') and not hasattr(self, '_shared'):
            raise TypeError('view castings to %r are not allowed' %
                            self.__class__.__name__)

        # note: view castings from `SyncedArray` to `SyncedArray` will not
        #  trigger the exception above, which is totally OK

        # 2) array creation by slicing (new-from-template) - e.g infoarr[:3]
        #    type(obj) is `SyncedArray`

        # detect construction from slice
        if hasattr(obj, '_shared') and not hasattr(self, '_shared'):
            # set the shared memory as attribute. Need this so that derived
            # arrays containing portions of the shared memory can still sync
            # operations
            self._shared = obj._shared

        # We do not need to return anything

    def __array_wrap__(self, out_arr, context=None):
        # return an `np.ndarray` after ufunc rather than `SyncedArray`
        return np.asarray(out_arr)

    #
    # define synchronized methods here
    for name in methods_to_sync:
        exec(method_sync_template % ((name,) * 2))


# create proxy objects for the sync classes above so we can access them from
# inside a separate process
mgr.SyncManager.register('Counter', SyncedCounter,
                         exposed=mgr.public_methods(SyncedCounter) +
                                 ['__next__'])
mgr.SyncManager.register('Array', SyncedArray,
                         exposed=(set(mgr.public_methods(SyncedArray)) |
                                  set(methods_to_sync) - {'__repr__'}))

if __name__ == '__main__':
    # some tests
    a = SyncedArray([1, 2, 3])
    a = SyncedArray(shape=4, fill=1)
