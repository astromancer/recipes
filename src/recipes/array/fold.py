"""
Memory efficient array folding (windowing) along any axis with optional overlap
between adjacent segments.  Overlapping segments are not duplicated in memory.
"""


# std
import numbers
import warnings

# third-party
import numpy as np
from numpy.lib.stride_tricks import as_strided

# relative
from ..string import Percentage


def resolve_size(size, n=None):

    # overlap specified by percentage string eg: 99% or timescale eg: 60s
    if isinstance(size, str):
        assert n, 'Array size `n` required if `size` given as percentage (str).'

        # percentage
        if size.endswith('%'):
            return round(Percentage(size).of(n))

    if isinstance(size, float):
        if size < 1:
            assert n, 'Array size `n` required if `size` given as percentage (float).'
            return round(size * n)

        raise ValueError('Providing a float value for `size` is only valid if '
                         'that value is smaller than 1, in which case it is '
                         'interpreted as a fraction of the array size.')

    if isinstance(size, numbers.Integral):
        return size

    raise ValueError(
        f'Invalid size: {size!r}. This should be an integer, or a percentage '
        'of the array size as a string eg: "12.4%", or equivalently a float < 1'
        ' eg: 0.124, in which case the array size should be supplied.'
    )


def _check_window_overlap(size, overlap, n, axis):
    # checks
    if n < size < 0:
        raise ValueError(f'Window size ({size}) should be greater than 0 and '
                         f'smaller than array size ({n}) along axis {axis}.')

    if size <= overlap < 0:
        raise ValueError(f'Overlap ({overlap}) should be greater equal 0 and '
                         f'smaller than window size ({size}).')


def fold(a, size, overlap=0, axis=0, pad='masked', **kws):
    """
    Fold (window) an array along a given `axis` at given window size `size`,
    with successive segments overlapping each previous segment by `overlap`
    number of elements. This method works on masked arrays as well, and will
    fold the mask identically to the data. By default the array is padded out
    with masked elements so that the step size evenly divides the array along
    the given axis.

    Parameters
    ----------
    a : array-like
        The array to be folded.
    size : int
        Window size in number of elements.
    overlap : int, optional
        Number of overlapping elements in each window, by default 0.
    axis : int, optional
        Axis along which to fold, by default 0.
    pad : str, optional
        Mode for padding, by default 'masked'.

    kws :
        Keywords are passed to `np.pad` which pads up the array to the required
        length.

    Returns
    -------
    np.ndarray or np.ma.MaskedArray
        The folded array.

    Notes
    -----
    When overlap is nonzero, the array returned by this function will have
    multiple entries **with the same memory location**.  Beware of this when
    doing inplace arithmetic operations on the returned array.
    eg.:
    >>> n, size, overlap = 2, 1, 1
    ... q = fold.fold(np.arange(n), size, overlap, pad=False)
    ... q
    array([[0, 1],
           [1, 2]])

    >>> k = 0
    ... q[0, overlap + k] *= 10
    ... q
    array([[ 0, 10],
           [10,  2]])

    """

    a = np.asanyarray(a)
    shape = a.shape
    n = shape[axis]

    # checks
    size = resolve_size(size, n)
    overlap = resolve_size(overlap, size)
    _check_window_overlap(size, overlap, n, axis)

    # short circuits
    if (n == size) and (overlap == 0):
        return a.reshape(np.insert(shape, axis, 1))

    if n < size:
        warnings.warn('Window size {} larger than array size {} along axis {}.',
                      size, n, axis)
        return a.reshape(np.insert(shape, axis, 1))

    # pad out
    if pad:
        a, _ = padder(a, size, overlap, axis, pad, **kws)
    #
    sa = get_strided_array(a, size, overlap, axis)

    # deal with masked data
    if np.ma.isMA(a):
        if np.ma.is_masked(a):
            mask = get_strided_array(a.mask, size, overlap, axis)
        else:
            mask = False

        sa = np.ma.array(sa.data, mask=mask)

    return sa


def is_null(x):
    """Check if an object is None or False."""
    return (x is None) or (x is False)


# FIXME: does not always pad out to the correct length!

def padder(a, size, overlap=0, axis=0, pad_mode='masked', **kws):
    """
    Pad the array out to the required length so a uniform fold can be made with
    no leftover elements.
    """
    a = np.asanyarray(a)  # convert to (un-masked) array
    n = a.shape[axis]

    # checks
    size = resolve_size(size, n)
    overlap = resolve_size(overlap, size)
    _check_window_overlap(size, overlap, n, axis)

    #
    mask = a.mask if np.ma.is_masked(a) else None
    step = size - overlap
    n_seg, leftover = divmod(n - overlap, step)  #
    if step == 1:
        leftover = size - 1

    if leftover:
        # default is to mask the "out of array" values
        # pad_mode = kws.pop('pad', 'mask')
        if (pad_mode == 'masked') and is_null(mask):
            mask = np.zeros(a.shape, bool)

        # pad the array at the end with `pad_end` number of values
        pad_end = size - leftover
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
    # note lines below relies on the array already being padded out
    new_shape = np.insert(a.shape, axis + 1, size)
    new_shape[axis] = a.shape[axis] // step  # number of segments
    # new shape is (..., n_seg, size, ...)

    # byte steps
    new_strides = np.insert(a.strides, axis, step * a.strides[axis])
    return as_strided(a, new_shape, new_strides, subok=True)


def ifold(a, size, overlap=0, axis=0, **kw):
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

    return returns[0 if len(returns) == 1 else ...]


def get_n_repeats(n, size, overlap):
    """
    Return an array of length n, with elements representing the number of
    times that the index corresponding to that element would be repeated in
    the strided array.
    """
    from recipes.lists import tally, cosort

    indices = fold(np.arange(n), size, overlap).ravel()
    if np.ma.is_masked(indices):
        indices = indices[~indices.mask]

    return cosort(*zip(*tally(indices).items()))[1]
