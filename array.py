import numpy as np
import numpy.core.numeric as _nx
from numpy.lib.stride_tricks import as_strided

from recipes.list import flatten, count_repeats, sortmore

#from IPython import embed


##########################################################################################################################################       
# Numpy recipies
##########################################################################################################################################
#****************************************************************************************************
class ArrayFolder(object):
    #FIXME: LAST SEGMENT WILL BE FOLDED.  this may not be desired
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, a, wsize, overlap=0, axis=0, **kw):
        return self.fold(a, wsize, overlap=0, axis=0, **kw)
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def fold(a, wsize, overlap=0, axis=0, **kw):
        '''
        segment an array at given wsize, overlap, 
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
        '''
        
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
        '''
        Generator version of fold.
        '''
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
        ''' '''
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
        ''' '''
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
        '''
        Return an array of length N, with elements representing the number of 
        times that the index corresponding to that element would be repeated in 
        the strided array.
        '''
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
        '''get window values + apply'''
        if window:
            windowVals = get_window(window, a.shape[-1])
            return a * windowVals
        else:
            return a




#====================================================================================================
def row_view(a):
    if a.ndim != 2:
        a = np.atleast_2d(a)
    a = np.ascontiguousarray(a)
    dt = np.dtype( (np.void, a.dtype.itemsize*a.shape[1]) )           #cast each row as a void type with same size as row--> this will be the element to uniquely identify
    return a.view(np.dtype(dt))

#====================================================================================================
def unique_rows(a, return_index=False, return_inverse=False):
    cast = row_view(a)
    res = np.unique(cast, return_index, return_inverse)
    if return_index or return_inverse:
        res, *rest = res
    unqarr = res.view(a.dtype).reshape(-1, a.shape[1])           #recast/reshape to original type/shape
    if return_index or return_inverse:
        return tuple([unqarr] + rest)
    else:
        return unqarr

#====================================================================================================
def row_intersection(a, b):
    ar, br = map(row_view, [a,b])
    return np.intersect1d(ar, br).view(a.dtype).reshape(-1, a.shape[1])
        
#====================================================================================================
def where_duplicate_array(a, axis=1):         
    #TODO:  impliment for ndarray
    cast = row_view(a)
    res, idx = np.unique(cast, return_index=0, return_inverse=1)
    return where_duplicate(idx)

#====================================================================================================
def where_close_array(a, precision=3, axis=1):         
    #TODO:  impliment for ndarray
    a = np.round(a, precision)
    cast = row_view(a)
    res, idx = np.unique(cast, return_index=0, return_inverse=1)
    return where_duplicate(idx)

#====================================================================================================
def arange_like(a):
        return np.arange(len(deltat))

#====================================================================================================
def multirange(*shape):
    N, dl = flatten(shape)
    return np.tile(range(dl), (N,1))

#====================================================================================================
#NOTE: TOO SLOW!!
#def grid_like(a):
    #'''create grid from the shape of the given array'''
    #return shape2grid( a.shape )

#====================================================================================================
def grid_like(a):
    '''create grid from the shape of the given array'''
    return np.mgrid[list(map(slice, a.shape))]


#====================================================================================================
def shape2grid(*shape):
    '''Creates an index grid from shape tuple. '''
    if len(shape)==1:                   #single argument passed - either tuple or number
        shape = shape[0]
    if isinstance( shape, int ):
        shape = shape,
    return range2grid( np.zeros_like(shape), shape )

#====================================================================================================
def range2grid(ixl, ixu):
    '''Use index ranges to construct and index grid'''
    slices = map(slice, ixl, ixu)
    return np.mgrid[tuple(slices)].astype(int)

#====================================================================================================
#NOTE: use hstack instead
#from recipes.iter import flatiter
#def flatten(a):
    #'''flatten arbitrarily nested iterator and return as array /TODO: masked array.'''
    ##if any(map(np.ma.isMA, a)):
    ##with warnings.catch_warnings():
    #return np.fromiter(flatiter(a), float)

#====================================================================================================



#====================================================================================================
#TODO: Make OO?? 
#class SubSet():
    #def __init__(self, a, centre, size)
        
        #pad                 = kw.pop('pad', 'edge').lower()
        #favour_upper        = kw.pop('favour_upper', True)
        #return_index        = kw.pop('return_index', 0)
        #fill_first          = kw.pop('fill_first', not kw.pop('window_first', False) )
        
        #rimap = { None      :       0,
                #'lower'   :       1,
                #'all'     :       2       }
        #if return_index in rimap:
            #return_index = rimap[return_index]

        
        ##type enforcement
        #mask        = a.mask       if np.ma.is_masked(a)   else None
        #a           = np.asarray(a)
        #size        = np.atleast_1d(size)
        #if len(size)==1:
            #size = np.ravel([size, size])
        
        ##assertions
        #pad_modes = ('constant', 'maximum', 'minimum', 'mean', 'median', 
                    #'reflect', 'symmetric', 'edge', 'linear_ramp', 'wrap', 
                    #'shift', 'clip')    #allowed modes
        #assert len(index) == a.ndim
        #assert pad in pad_modes
        ##assert return_index in (0,1)
        
    #def 
        
    ##
    ##@print_args()
    ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def spillage(a, ixl, ixu):
        #'''check which index ranges are smaller/larger than the array dimensions'''
        #under = ixl < 0
        #over = ixu >= a.shape
        #return under, over

    ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def shift(a, ixl, ixu):
        #'''so they start at 0'''
        #under, over = spillage(a, ixl, ixu)
        #ixu[under] -= ixl[under] #shift the indices upward
        #ixl[under] = 0
        #return ixl, ixu
    
    ##@print_args()
    ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def take_from_ranges(a, ixl, ixu):
        #'''Return items within index ranges from the array'''
        #return a[ tuple(range2grid(ixl,ixu)) ]
    
    ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def _return(a, ixl, ixu):
        #'''return stuff'''
        #if return_index == 0:
            #return take_from_ranges(a, ixl, ixu)
        
        #if return_index == 1:
            #return take_from_ranges(a, ixl, ixu), ixl
        
        #if return_index == 2:
            #grid = range2grid(ixl, ixu)
            #return a[ tuple(grid) ], tuple(grid)
            
            
            
#====================================================================================================
def neighbours(a, index, size, **kw):
    '''
    Return nearest neighbour window centered on index.  N-d implementation with optional 
    padding for edge handeling.
    
    Parameters
    ----------
    a   :               array-like
        input array
    index :               array-like
        index position for which neighbours will be returned
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
            2 or 'all'          - return full window index grid
    fill_first:         bool - optional, default True
        Whether to fill the missing indices (edge values accoring to mode) before doing the 
        windowing or after.
    window_first:         bool - optional, default True
        Does the opposite of fill_first.  Keyword redundancy for convenience.  If both keywords
        are give, the value of fill_first will supercede.
    
    Returns
    -------
    Function always return `size` items except when mode='clip' in which case the number of 
    returned values will be determined by the array shape.
    '''
    
    #default arguments
    #TODO:  TRANSDICT!!
    pad                 = kw.pop('pad', 'edge').lower()
    favour_upper        = kw.pop('favour_upper', True)
    return_index        = kw.pop('return_index', 0)
    fill_first          = kw.pop('fill_first', not kw.pop('window_first', False) )
    
    rimap = { None      :       0,
              'lower'   :       1,
              'all'     :       2       }
    if return_index in rimap:
        return_index = rimap[return_index]

    
    #type enforcement
    mask        = a.mask       if np.ma.is_masked(a)   else None
    a           = np.asarray(a)
    size        = np.atleast_1d(size)
    if len(size)==1:
        size = np.ravel([size, size])
    
    #assertions
    pad_modes = ('constant', 'maximum', 'minimum', 'mean', 'median', 
                 'reflect', 'symmetric', 'edge', 'linear_ramp', 'wrap', 
                 'shift', 'clip')    #allowed modes
    assert len(index) == a.ndim
    assert pad in pad_modes
    #assert return_index in (0,1)
    
    #
    #@print_args()
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def spillage(a, ixl, ixu):
        '''check which index ranges are smaller/larger than the array dimensions'''
        under = ixl < 0
        over = ixu >= a.shape
        return under, over

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def shift(a, ixl, ixu):
        '''so they start at 0'''
        under, over = spillage(a, ixl, ixu)
        ixu[under] -= ixl[under] #shift the indices upward
        ixl[under] = 0
        return ixl, ixu
    
    #@print_args()
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def take_from_ranges(a, ixl, ixu):
        '''Return items within index ranges from the array'''
        return a[ tuple(range2grid(ixl,ixu)) ]
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _return(a, ixl, ixu):
        '''return stuff'''
        if return_index == 0:
            return take_from_ranges(a, ixl, ixu)
        
        if return_index == 1:
            return take_from_ranges(a, ixl, ixu), ixl
        
        if return_index == 2:
            grid = range2grid(ixl, ixu)
            return a[tuple(grid)], tuple(grid)
        

    #determine index ranges of return elements for each dimension
    div = np.floor_divide(size, 2)
    uneven = np.mod(size, 2).astype(bool)      #True on axis for which window size is uneven
    ixl = index - div + (favour_upper & (~uneven)) #
    ixu = index + div + (favour_upper | uneven)
    ixl = ixl.astype(int)
    ixu = ixu.astype(int)
    #print(uneven, favour_upper & (~uneven), favour_upper | uneven)
    #print(ixl, ixu)
    
    #clip to array edge
    if pad == 'clip':
        #clip indices for which window bigger than array dimension
        ixl, ixu = np.clip( [ixl,ixu], np.zeros(a.ndim,int), a.shape )
        return _return(a, ixl, ixu)
        
    #shift central index position so that the first/last `size` items are returned
    if pad == 'shift':
        
        ashape = np.array(a.shape)
        assert ~any(a.shape < size)
        
        under, over = spillage(a, ixl, ixu)
        
        #print(under, over)
        
        ixu[over] = ashape[over]
        ixl[over] = ixu[over] - size[over]
            
        ixl[under] = 0
        ixu[under] = ashape[under]
        #NOTE: same as:          ixl, ixu =  shift(a, ixl, ixu)
        
        #print(ixl, ixu)
        
        return _return(a, ixl, ixu)
    
    if fill_first:
        #determine pad widths
        pl = -ixl
        pl[pl<0] = 0
        pu = ixu - a.shape
        pu[pu<0] = 0
        padwidth = tuple(zip(pl,pu))
        #print(padwidth)
        #pad the array / mask
        padded = np.pad(a, padwidth, pad, **kw)
        
        #save return indices if requested
        if return_index == 1:
            ri = ixl[:]
        
        #shift index ranges upward (padding extends the array, so we need to adjust the indices)
        ixl, ixu =  shift(a, ixl, ixu)
        win = take_from_ranges(padded, ixl, ixu)
    
    #else:
        #TODO:  YOU CAN DECORATE np.pad to accomplish this functionality
        if not mask is None:
            if not mask is False:
                mask = np.pad(mask, padwidth, pad, **kw)
                mask = take_from_ranges(mask, ixl, ixu)
            win = np.ma.array( win, mask=mask )
        
        if return_index == 0:
            return win
        
        if return_index == 1:
            return win, ri
        
        if return_index == 2:
            grid = range2grid(np.zeros(a.ndim,int), a.shape)
            #FIXME:  this is probs quite inefficient!!
            ri = tuple(neighbours(g, index, size, **kw) for g in grid)
            return win, ri
        
        


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from sklearn.neighbors import NearestNeighbors
#****************************************************************************************************
class NearestNeighbours(NearestNeighbors):
    '''fix these aggregious american spelling errors'''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def kneighbours(self, X=None, n_neighbors=None, return_distance=True):
        return self.kneighbors(X, n_neighbors, return_distance)

    #TODO: fill method!
    
#====================================================================================================
def neighbour_fill(data, fill_these=None, hood=None, method='median', k=5, **kw):
    '''
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
    '''
    
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
    
    
    grid = grid_like(data)
    
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
        fillvals = np.squeeze(scipy.stats.mode(nn, axis=0)[0])  #Will not work with sigma clipping
    
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