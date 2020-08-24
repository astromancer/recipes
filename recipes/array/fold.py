# std libs
import warnings

# third-party libs
import numpy as np
from numpy.lib.stride_tricks import as_strided


def _checks(wsize, overlap, n, axis):
    # checks
    if n < wsize < 0:
        raise ValueError(f'Window size ({wsize}) should be greater than 0 and '
                         f'smaller than array size ({n}) along axis {axis}')
    if wsize <= overlap < 0:
        raise ValueError(f'Overlap ({overlap}) should be greater equal 0 and '
                         f'smaller than window size ({wsize})')


def fold(a, wsize, overlap=0, axis=0, pad='masked', **kws):
    """
    Fold (window) an array along a given `axis` at given `size`, with successive
    windows overlapping each previous by `overlap` elements.  This method
    works on masked arrays as well and will fold the mask identically to the
    data. By default the array is padded out with masked elements so that the
    step size evenly divides the array along the given axis.

    Parameters
    ----------
    a
    wsize
    overlap
    axis
    pad
    kws
        Keywords are passed to `np.pad` which pads up the array to the required
        length.

    Returns
    -------

    Notes
    -----
    When overlap is nonzero, the array returned by this function will have
    multiple entries **with the same memory location**.  Beware of this when
    doing inplace arithmetic operations on the returned array.
    eg.:
    >>> n, size, overlap = 100, 10, 5
    >>> q = fold(np.arange(n), size, overlap)
    >>> k = 0
    >>> q[0, overlap + k] *= 10
    >>> q[1, k] == q[0, overlap + k]  # is True

    """
    a = np.asanyarray(a)
    shape = a.shape
    n = shape[axis]

    _checks(wsize, overlap, n, axis)

    # short circuits
    if (n == wsize) and (overlap == 0):
        return a.reshape(np.insert(shape, axis, 1))

    if n < wsize:
        warnings.warn(
                f'Window size larger than array size along dimension {axis}')
        return a.reshape(np.insert(shape, axis, 1))

    # pad out
    if pad:
        a, n_seg = padder(a, wsize, overlap, axis, **kws)
    #
    sa = get_strided_array(a, wsize, overlap, axis)

    # deal with masked data
    if np.ma.isMA(a):
        mask = a.mask
        if mask is not False:
            mask = get_strided_array(mask, wsize, overlap, axis)
        sa = np.ma.array(sa.data, mask=mask)

    return sa


def is_null(x):
    return (x is None) or (x is False)


def padder(a, wsize, overlap=0, axis=0, pad_mode='masked', **kws):
    """ """
    a = np.asanyarray(a)  # convert to (un-masked) array
    n = a.shape[axis]

    # checks
    _checks(wsize, overlap, n, axis)

    #
    mask = a.mask if np.ma.is_masked(a) else None
    step = wsize - overlap
    n_seg, leftover = divmod(n, step)  #
    if step == 1:
        leftover = wsize - 1

    if leftover:
        # default is to mask the "out of array" values
        # pad_mode = kws.pop('pad', 'mask')
        if (pad_mode == 'masked') and is_null(mask):
            mask = np.zeros(a.shape, bool)

        # pad the array at the end with `pad_end` number of values
        pad_end = wsize - leftover
        pad_width = np.zeros((a.ndim, 2), int)  # initialise pad width indicator
        pad_width[axis, -1] = pad_end
        pad_width = list(map(tuple, pad_width))  # map to list of tuples

        # pad (apodise) the input signal (and mask)
        if pad_mode == 'masked':
            a = np.pad(a, pad_width, 'constant', constant_values=0)
            mask = np.pad(mask, pad_width, 'constant', constant_values=True)
        else:
            a = np.pad(a, pad_width, pad_mode, **kws)
            if not is_null(mask):
                mask = np.pad(mask, pad_width, pad_mode, **kws)

    # convert back to masked array
    if not is_null(mask):
        a = np.ma.array(a, mask=mask)

    return a, int(n_seg)


def get_strided_array(a, size, overlap, axis=0):
    """
    Fold array `a` along axis `axis` with window size of `size`, each
    consecutive segment overlapping previous by `overlap` elements.
    Use array strides (byte-steps) for memory efficiency.  The new axis is
    inserted in the position before `axis`.

    Parameters
    ----------
    a
    size
    overlap
    axis

    Returns
    -------

    """
    if axis < 0:
        axis += a.ndim

    step = size - overlap
    # if padded:
    # note line below relies on the array already being padded out
    n_segs = (a.shape[axis] - overlap) // step  # number of segments
    new_shape = np.insert(a.shape, axis + 1, size)
    new_shape[axis] = n_segs
    # new shape is (..., n_seg, size, ...)

    # byte steps
    new_strides = np.insert(a.strides, axis, step * a.strides[axis])
    return as_strided(a, new_shape, new_strides)


def gen(a, size, overlap=0, axis=0, **kw):
    """
    Generator version of fold.
    """
    a, n_seg = padder(a, size, overlap, **kw)
    step = size - overlap
    i = 0
    while i < n_seg:
        start = i * step
        stop = start + size
        ix = [slice(None)] * a.ndim
        ix[axis] = slice(start, stop)
        yield a[ix]
        i += 1


def rebin(x, binsize, t=None, e=None):
    """
    Rebin time series data. Assumes data are evenly sampled in time (constant
     time steps).
    """
    xrb = fold(x, binsize).mean(1)
    returns = (xrb,)

    if t is not None:
        trb = np.median(fold(t, binsize), 1)
        returns += (trb,)

    if e is not None:
        erb = np.sqrt(np.square(fold(e, binsize)).mean(1))
        returns += (erb,)

    if len(returns) == 1:
        return returns[0]
    return returns

# def get_nocc(N, wsize, overlap):
#     """
#     Return an array of length N, with elements representing the number of
#     times that the index corresponding to that element would be repeated in
#     the strided array.
#     """
#     from recipes.containers.lists import count_repeats, sortmore
#
#     I = fold(np.arange(N), wsize, overlap).ravel()
#     if np.ma.is_masked(I):
#         I = I[~I.mask]
#
#     d = count_repeats(I)
#     ix, noc = sortmore(*zip(*d.items()))
#     return noc
