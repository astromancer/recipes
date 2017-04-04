import  ctypes
import multiprocessing as mp

import numpy as np

#****************************************************************************************************
class SyncedCounter(object):
    '''
    synchronized shared counter

    Bonus: since we've now placed a more coarse-grained lock on the modification
    of the value, we may throw away Value with its fine-grained lock altogether,
    and just use multiprocessing.RawValue, that simply wraps a shared object
    without any locking.

    Value values are locked by default. This is correct in the sense that even
    if an assignment consists of multiple operations (such as assigning a string
    which might be many characters) then this assignment is atomic. However, when
    incrementing a counter you'll still need an external lock, because
    incrementing loads the current value and then increments it and then assigns
    the result back to the Value.

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
    '''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, initval=0):
        self.val = mp.Value('i', initval)
        self.lock = mp.Lock()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __str__(self):
        return str(self.val.value)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __repr__(self):
        return str(self.val.value)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __iadd__(self, val):
        with self.lock:
            self.val.value += val
        return self

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __mod__(self, val):
        with self.lock:
            return self.val.value % val

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def inc(self, val=1):
        with self.lock:
            self.val.value += val

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def value(self):
        with self.lock:
            return self.val.value



#****************************************************************************************************
class SyncedArray(np.ndarray):
    '''
    Wrapper class for synchronized parallel write access to shared memory with
    all the numpy indexing / slicing niceties.

    Notes:
        see http://eli.thegreenplace.net/2012/01/04/shared-counter-with-pythons-multiprocessing
    '''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __new__(cls, data=None, shape=None, fill_value=0, dtype=ctypes.c_double):
        # Create the ndarray instance of our type, given the usual
        # ndarray input arguments.  This will call the standard
        # ndarray constructor, but return an object of our type.
        # It also triggers a call to NDArray.__array_finalize__
        #print( 'In __new__ with class %s' % cls)

        if data is None and shape is None:
            raise ValueError('Need either data or shape, or both')

        if not data is None:
            data = np.asarray(data).reshape(shape)
        else:
            data = np.full(shape, fill_value, np.dtype(dtype))

        shx = mp.Array(dtype, data.size)
        shx[:] = data.ravel()

        #constructor
        obj = np.ndarray.__new__(cls, data.shape, dtype, buffer=shx.get_obj())

        #print('last bit of __new__ with class %s' % cls)
        obj._shared = shx

        #create the object
        #obj = np.ndarray.__new__(cls, data.shape, dtype, buffer=shx.get_obj())
        #obj._lock = mp.Lock()

        ## Finally, we must return the newly created object:
        return obj

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __array_finalize__(self, obj):
        #print('In array_finalize:')
        #print('   self type is %s' % type(self))
        #print('   obj type is %s' % type(obj))
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

        # From view casting - e.g arr.view(InfoArray):
        #    obj is arr
        #    (type(obj) can be InfoArray)
        # From new-from-template - e.g infoarr[:3]
        #    type(obj) is InfoArray
        #
        # Note that it is here, rather than in the __new__ method,
        # that we set the default value for 'info', because this
        # method sees all creation of default objects - with the
        # InfoArray.__new__ constructor, but also with
        # arr.view(InfoArray).
        self._shared = None  #getattr(obj, 'shared', None)

        #TODO: can you return a numpy array here??

        # We do not need to return anything

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __array_wrap__(self,  out_arr, context=None):
        #return an array ofter ufunc rather than MetaArray
        return np.asarray(out_arr)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __setitem__(self, key, val):
        #TODO: optional context manager...??
        if self._shared:
            with self._shared.get_lock(): # synchronize access
                return super().__setitem__(key, val)
        else:
            #FIXME NOT  SURE WHY THIS IS HERE
            return super().__setitem__(key, val)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __iadd__(self, val):
        if self._shared:
            with self._shared.get_lock():
                super().__iadd__(val)
        else:
            return super().__iadd__(val)
        return self

    #def __mul__(self,o):
        #pass
    #def __truediv__(self,o):
        #pass
    #def __pow__(self,o):
        #pass

    #def __mul__(self,o):
        #pass
    #def __truediv__(self,o):
        #pass
    #def __pow__(self,o):
        #pass

    #def __lt__(self, b):
        #pass
    #def __le__(self, b):
        #pass
    #def __eq__(a, b):
        #pass
    #def __ne__(a, b):
        #pass
    #def __ge__(a, b):
        #pass
    #def __gt__(a, b):
        #pass