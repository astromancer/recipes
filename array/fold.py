"""
Algorithms for folding Nd arrays
"""

import numpy as np
from numpy.lib.stride_tricks import as_strided

from recipes.list import count_repeats, sortmore

class ArrayFolder(object):
    #TODO: docstring
    #FIXME: LAST SEGMENT WILL BE FOLDED.  this may not be desired
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, a, wsize, overlap=0, axis=0, **kw):
        return self.fold(a, wsize, overlap=0, axis=0, **kw)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def fold(a, wsize, overlap=0, axis=0, **kw):
        """
        Segment an array at given wsize, overlap,
        optionally applying a windowing function to each
        segment.

        keywords are passed to np.pad used to fill up the array to the required length.  This
        method works on multidimentional and masked array as well.

        keyword arguments are passed to np.pad to fill up the elements in the last window (default is
        symmetric padding).

        NOTE: When overlap is nonzero, the array returned by this function will have multiple entries
        **with the same memory location**.  Beware of this when doing inplace arithmetic operations.
        e.g.
        N, wsize, overlap = 100, 10, 5
        q = ArrayFolder.fold(np.arange(N), wsize, overlap )
        k = 0
        q[0,overlap+k] *= 10
        q[1,k] == q[0,overlap+k]  #is True
        """

        a, Nseg = ArrayFolder.pad(a, wsize, overlap, **kw)
        sa = ArrayFolder.get_strided_array(a, wsize, overlap, axis)

        #deal with masked data
        if np.ma.isMA(a):
            mask = a.mask
            if not mask is False:
                mask = ArrayFolder.get_strided_array(mask, wsize, overlap)
            sa = np.ma.array(sa, mask=mask)

        return sa

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def gen(a, wsize, overlap=0, axis=0, **kw):
        """
        Generator version of fold.
        """
        a, Nseg = ArrayFolder.pad(a, wsize, overlap, **kw)

        step = wsize - overlap

        #TODO: un-nest me
        get_slice = lambda i: [slice(i*step, i*step+wsize) if j==axis else slice(None)
                                    for j in range(a.ndim)]
        i = 0
        while i < Nseg:
            yield a[get_slice(i)]
            i += 1

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def enumerate(a, wsize, overlap=0, axis=0, **kw):
        yield from enumerate(ArrayFolder.gen(a, wsize, overlap, axis, **kw))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def pad(a, wsize, overlap=0, axis=0, **kw):
        """ """
        assert wsize > 0, 'wsize > 0'
        assert overlap >= 0, 'overlap >= 0'
        assert overlap < wsize, 'overlap < wsize'

        mask = a.mask   if np.ma.is_masked(a)   else None
        a = np.asarray(a)       #convert to (un-masked) array
        N = a.shape[axis]
        step = wsize - overlap
        Nseg, leftover = divmod(N-overlap, step)

        if leftover:
            pad_mode = kw.pop('pad', 'mask')       #default is to mask the "out of array" values
            if pad_mode == 'mask' and (mask in (None, False)):
                mask = np.zeros(a.shape, bool)

            pad_end = step - leftover
            pad_width = np.zeros((a.ndim, 2), int)  #initialise pad width indicator
            pad_width[axis, -1] = pad_end           #pad the array at the end with 'pad_end' number of values
            pad_width = list(map(tuple, pad_width)) #map to list of tuples

            #pad (apodise) the input signal (and mask)
            if pad_mode == 'mask':
                a = np.pad(a, pad_width, 'constant', constant_values=0)
                mask = np.pad(mask, pad_width, 'constant', constant_values=True)
            else:
                a = np.pad(a, pad_width, pad_mode, **kw)
                if mask not in (None, False):
                    mask = np.pad(mask, pad_width, pad_mode, **kw)

        #convert back to masked array
        if not mask is None:
            a = np.ma.array(a, mask=mask)

        return a, int(Nseg)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def get_strided_array(a, size, overlap, axis=0):
        """ """
        if axis<0:
            axis += a.ndim
        step = size - overlap
        other_axes = np.setdiff1d(range(a.ndim), axis) #indeces of axes which aren't stepped along

        new_shape = np.zeros(a.ndim, int)
        new_shape[0] = (a.shape[axis] - overlap) // step    #Nwindows
        new_shape[1:] = np.take(a.shape, other_axes)
        new_shape = np.insert(new_shape, axis+1, size)

        new_strides = (step * a.strides[axis],) + a.strides

        return as_strided(a, new_shape, new_strides)


    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def get_nocc(N, wsize, overlap):
        """
        Return an array of length N, with elements representing the number of
        times that the index corresponding to that element would be repeated in
        the strided array.
        """
        I = ArrayFolder.fold(range(N), wsize, overlap)
        d = count_repeats(I.ravel())
        ix, noc = sortmore(*zip(*d.items()))
        return noc

ArrayFolding = ArrayFolder

#****************************************************************************************************
class WindowedArrayFolder(ArrayFolder):
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def fold(a, wsize, overlap=0, axis=0, **kw):
        window = kw.pop('window', None)
        sa = ArrayFolder.fold(a, wsize, overlap, axis, **kw)
        return ArrayFolder.windowed(sa, window)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def gen(a, wsize, overlap=0, axis=0, **kw):
        window = kw.pop('window', None)
        for sub in ArrayFolder.gen(a, wsize, overlap, axis, **kw):
            yield  ArrayFolder.windowed(sub, window)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def windowed(a, window=None):
        """get window values + apply"""
        if window:
            windowVals = get_window(window, a.shape[-1])
            return a * windowVals
        else:
            return a