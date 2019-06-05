
# third-party libs
import numpy as np
from IPython import embed
from sklearn.neighbors import NearestNeighbors

# relative libs
from . import ndgrid



#TODO: optimize - class with dynamically generated methods?

def neighbours(a, centre, size, **kws):
    """
    Return nearest neighbour sub-window centered on *centre*.  N-d implementation with optional
    padding for edge handling.

    Parameters
    ----------
    a   :               array-like
        input array
    centre :               array-like
        centre position for which neighbours will be returned
    size   :            array-like
        size of neighbourhood.

    Keywords
    --------
    mode:               str
        mode by which selection will take place
    favour_upper:       bool
        For even size - whether the upper neighbourhood should be returned, or the lower.
    return_index:       int
        Whether to return the indices:
            0 or None           - No indices returned
            1 or 'lower'        - return window lower indices
            2 or 'slice'        - return slices
            3 or 'all'          - return full window index grid
    fill_first:         bool - optional, default True
        Whether to fill the missing indices (edge values accoring to mode) before doing the
        windowing or after.
    window_first:         bool - optional, default True
        Does the opposite of fill_first.  Keyword redundancy for convenience.  If both keywords
        are give, the value of fill_first will supersede.

    Returns
    -------
    Function always return `size` items except when mode='clip' in which case the number of
    returned values will be determined by the array shape.
    """

    # default arguments
    # TODO:  Translate keywords!!
    pad = kws.pop('pad', 'edge').lower()
    favour_upper = kws.pop('favour_upper', True)
    fill_first = kws.pop('fill_first', not kws.pop('window_first', False))
    return_index = kws.pop('return_index', 0)
    rimap = {None: 0,
             'lower': 1,
             slice: 2, 'slice' : 2,
             all: 3, 'all' : 3}
    # TODO: sparse grid??
    if return_index in rimap:
        return_index = rimap[return_index]
    if return_index not in [0, 1, 2, 3]:
        raise ValueError('bad return_index: %s', return_index)

    # type enforcement
    mask = a.mask if np.ma.is_masked(a) else None
    a = np.asarray(a)
    ashape = np.array(a.shape)
    # duplicate size to (x, y) if necessary
    size = np.atleast_1d(size)
    if len(size) == 1:
        size = np.ravel([size, size])
    # size = np.r_[size, size][:2]       # slower one-liner

    # checks
    pad_modes = ('constant', 'maximum', 'minimum', 'mean', 'median',
                 'reflect', 'symmetric', 'edge', 'linear_ramp', 'wrap',
                 'shift', 'clip', 'mask')  # allowed modes
    assert len(centre) == a.ndim
    assert pad in pad_modes
    assert np.all(size < a.shape)       # FIXME: this may only sometimes imply an error
                                        # FIXME: shoud be ok with pad='mask'
    # assert return_index in (0,1)

    # determine index ranges of return elements for each dimension
    div = np.floor_divide(size, 2)
    uneven = np.mod(size, 2).astype(bool)  # True on axis for which window size is uneven
    ixl = centre - div + (favour_upper & (~uneven))  #
    ixu = centre + div + (favour_upper | uneven)
    ixl = ixl.round().astype(int)
    ixu = ixu.round().astype(int)

    under, over = spillage(a, ixl, ixu)

    if pad == 'mask':

        # NOTE: YOU could use pad='constant', constant_values=np.nan. then mask the nans??
        # this may help integrate the code below more tightly

        if not (over.any() or under.any()):
            return _return(a, ixl, ixu, return_index)

        # get array segment to use
        ixl_ = np.where(under, (0, 0), ixl)
        ixu_ = np.where(over, ashape, ixu)
        a_slice = tuple(map(slice, ixl_, ixu_))

        # get sub
        ixls = np.where(under, -ixl, (0,0))
        ixus = np.where(over, ixu_ - ixl_, size)
        sub_slice = tuple(map(slice, ixls, ixus))
        sub = np.ma.empty(size, a.dtype)


        # embed()

        # if mask is not None:
        #     if mask is False:
        #         sub_mask = True
        #     else:
        #         sub_mask = mask[a_slice]
        # else:
        #     sub_mask = True

        # put the data in the sub-array
        sub.mask = True                 # mask the entire array
        sub[sub_slice] = a[a_slice]     # set the data (overwrite masked)

        if return_index == 0:
            return sub

        if return_index == 1:
            return sub, ixl_

        if return_index == 2:
            return sub, a_slice

        if return_index == 3:
            return sub, ndgrid.like(a)[:, a_slice]

        return sub

    # clip to array edge
    if pad == 'clip':       #TODO: 'shrink' may be more apt
        # clip indices for which window bigger than array dimension
        # logging.debug('clipping', ixl, ixu)
        ixl, ixu = np.clip([ixl, ixu], np.zeros(a.ndim, int), a.shape)
        # logging.debug('clipped', ixl, ixu)
        return _return(a, ixl, ixu, return_index)

    # shift central index position so that the first/last `size` items are returned
    if pad == 'shift':
        assert ~any(a.shape < size)

        ixu[over] = ashape[over]
        ixl[over] = ixu[over] - size[over]
        ixl[under] = 0
        ixu[under] = size[under]


        return _return(a, ixl, ixu, return_index)

    # if fill_first:
    # determine pad widths
    pl = -ixl
    pl[pl < 0] = 0
    pu = ixu - a.shape
    pu[pu < 0] = 0
    padwidth = tuple(zip(pl, pu))

    # print(padwidth)
    # pad the array / mask
    try:
        padded = np.pad(a, padwidth, pad, **kws)
    except:
        from IPython import embed
        embed()
        raise

    # save return indices if requested
    if return_index == 1:
        ri = ixl[:]

    # shift index ranges upward (padding extends the array, so we need to adjust the indices)
    ixl, ixu = shift(a, ixl, ixu)
    sub = take_from_ranges(padded, ixl, ixu)

    # else:
    # TODO:  YOU CAN DECORATE np.pad to accomplish this functionality
    if not mask is None:
        if not mask is False:
            mask = np.pad(mask, padwidth, pad, **kws)
            mask = take_from_ranges(mask, ixl, ixu)
        sub = np.ma.array(sub, mask=mask)

    if return_index == 0:
        return sub

    if return_index == 1:
        return sub, ri

    if return_index == 2:
        grid = ndgrid.like(a)
        gpadded = np.pad(grid, padwidth, pad, **kws)
        ix = take_from_ranges(gpadded, ixl, ixu)
        return sub, ix




# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def spillage(a, ixl, ixu):
    """check which index ranges are smaller/larger than the array dimensions"""
    under = ixl < 0
    over = ixu >= a.shape
    return under, over


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def shift(a, ixl, ixu):
    """so they start at 0"""
    under, over = spillage(a, ixl, ixu)
    ixu[under] -= ixl[under]  # shift the indices upward
    ixl[under] = 0
    return ixl, ixu


# @print_args()
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def take_from_ranges(a, ixl, ixu):
    """Return items within index ranges from the array"""
    return a[tuple(map(slice, ixl, ixu))]
    # return a[tuple(ndgrid.from_ranges(ixl, ixu))]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _return(a, ixl, ixu, return_index):
    """return stuff"""
    if return_index == 0:
        return take_from_ranges(a, ixl, ixu)

    if return_index == 1:
        return take_from_ranges(a, ixl, ixu), ixl

    slices = tuple(map(slice, ixl, ixu))
    if return_index == 2:
        return a[slices], slices

    if return_index == 3:
        grid = np.mgrid[slices].astype(int)
        return a[slices], tuple(grid)






#****************************************************************************************************
class NearestNeighbours(NearestNeighbors):
    """fix these aggregious american spelling errors"""
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def kneighbours(self, X=None, n_neighbors=None, return_distance=True):
        return self.kneighbors(X, n_neighbors, return_distance)

    #TODO: fill method!

#====================================================================================================
def fill(data, fill_these=None, hood=None, method='median', k=5, **kw):
    """
    Fill invalid values with values from data selected from k nearest
    neighbours in hood

    Parameters
    ----------
    data        :       array-like
        data array
    fill_these  :       boolean array - optional
        array that specifies the coordinates of the values to be filled
    hood        :       boolean array - optional
        array that specifies the coordinates of the values that are allowed as
        neighbours - i.e. the neighbourhood
    method      :       str - {mean, median, mode, weighted, random}; default 'median'
        how the filling values are to be chosen
    k           :       int - default 5
        the number of neighbours to select from

    Keywords
    --------
    return_filled       :       bool - default True
        return the filled array
    return_filling      :       bool - default False
        return the nearest neighbour data as flattened array
    return_index        :       bool - default False
        return the indeces of the nearest neighbours

    Returns
    -------
    array or tuple of arrays depending on keywords
    """

    #TODO: OO
    #TODO: N-d implementation
    #TODO: Debug option!!
    known_methods = {'mean', 'median', 'mode', 'weighted', 'random'}
    if not method in known_methods:
        raise ValueError('Unrecognised method: {}'.format(method))

    with_sigma_clipping = kw.pop('with_sigma_clipping', True)

    return_filled = kw.pop('return_filled', True)     #return the filled array
    return_filling = kw.pop('return_filling', False)  #return the nearest neighbour data as flattened array
    return_index = kw.pop('return_index', False)      #return the indeces of the nearest neighbours

    grid = ndgrid.like(data)

    if fill_these is None:
        fill_these = data.mask
    else:
        #NOTE: if there are masked values in data THEY WILL NOT BE FILLED
        pass

    if ~fill_these.any():
        if return_filled:
            return data
        else:
            return ()

    if hood is None:
        hood = ~fill_these    #will bork if not MA
    else:       #if np.ma.isMA(data):
        hood = hood & ~fill_these   #so we don't pick from the masked pixels

    #establish good and bad data coordinates.  Bad to be filled from nearest good neighbours
    good = yg, xg = grid[:,hood]
    bad = grid[:,fill_these]

    #fill values from given axis only (eg. fill from rows or columns exclusively)
    #NOTE: This is much faster than providing explicit direction weighted metric
    axis = kw.pop( 'axis', None )
    if not axis is None:        #NOTE: rather than doing this, one can just fit 1d data...
        f = 100  #this will make a pick from the other axes *f* times as unlikely
        other_axes = np.setdiff1d( range(data.ndim), axis)
        good[other_axes] *= f
        bad[other_axes] *= f
    else:
        f = 1
        other_axes = np.arange( data.ndim )

    #Get k nearest neighbour pixel values
    knn = NearestNeighbours(k, **kw).fit( good.T )
    _ix = knn.kneighbours(bad.T, return_distance=False).astype(int)     #_ix = knn.kneighbours(bad.T, return_distance=False )

    if not axis is None:
        good[other_axes] = (good[other_axes] / f).astype(int)       #good[other_axes] /= f
        bad[other_axes] = (bad[other_axes] / f).astype(int)         #bad[other_axes] /= f


    ix = good.T[_ix]            #image pixel coordinates of nearest neighbours
    nn = data[tuple(ix.T)]      #nearest neighbour pixel value
    nn = np.atleast_2d(nn)


    if with_sigma_clipping:     #HACK
        from astropy.stats import sigma_clip

        nn = sigma_clip(nn, )
        p = (~nn.mask).astype(float)
        p /= p.sum(0)
    else:
        nn = np.ma.array(nn)  #make it masked array
        p = np.ones_like(nn) / nn.size

    #av= {'mean'         :       np.mean,
        #'median'       :       np.median,
        #'mode'         :       scipy.stats.mode}


    if method == 'mean':
        fillvals = np.ma.mean(nn, axis=0)

    if method=='median':
        fillvals = np.ma.median(nn, axis=0)

    if method=='mode':
        from scipy.stats import mode
        fillvals = np.squeeze(mode(nn, axis=0)[0])  # Will not work with sigma clipping

    if method=='weighted':
        weights = kw['weights']
        w = weights[ tuple(ix.T) ]
        fillvals = np.average(nn, axis=1, weights=w.T)

    if method=='random':
        m, n = nn.shape
        selection = np.empty(n, int)

        for i, (r, rp) in enumerate(zip(nn.T, p.T)):
            selection[i] = np.random.choice(m, 1, p=rp)         #generate random integers
        selection = (selection, np.arange(n))

        fillvals = nn[selection]
        if return_index:
            ix = ix[selection[::-1]]

    out = ()
    if return_filled:
        filled = data.copy()
        filled[tuple(bad)] = fillvals
        out += (filled,)
    if return_filling:
        out += (fillvals,)
    if return_index:
        out += (ix,)

    if len(out)==1:
        out = out[0]
    return out







if __name__ == '__main__':
    # do some tests here
    a = np.random.randn(10, 10)

    for pad in ('shift', 'clip', 'mask'):
        neighbours(a, (8,8), (4,4), pad=pad)
