"""
Common algorithms involving arrays
"""
import numpy as np

from recipes.list import flatten, where_duplicate


# from IPython import embed


def is_broadcastable(shp1, shp2):
    for a, b in zip(shp1[::-1], shp2[::-1]):
        if a == 1 or b == 1 or a == b:
            pass
        else:
            return False
    return True


# ====================================================================================================
def row_view(a):
    if a.ndim != 2:
        a = np.atleast_2d(a)
    a = np.ascontiguousarray(a)
    # cast each row as a void type with same size as row--> this will be the element to uniquely identify
    dt = np.dtype((np.void, a.dtype.itemsize * a.shape[1]))
    return a.view(np.dtype(dt))


# ====================================================================================================
def unique_rows(a, return_index=False, return_inverse=False):
    cast = row_view(a)
    res = np.unique(cast, return_index, return_inverse)
    if return_index or return_inverse:
        res, *rest = res
    unqarr = res.view(a.dtype).reshape(-1, a.shape[1])  # recast/reshape to original type/shape
    if return_index or return_inverse:
        return tuple([unqarr] + rest)
    else:
        return unqarr


# ====================================================================================================
def row_intersection(a, b):
    ar, br = map(row_view, [a, b])
    return np.intersect1d(ar, br).view(a.dtype).reshape(-1, a.shape[1])


# ====================================================================================================
def where_duplicate_array(a, axis=1):
    # TODO:  impliment for ndarray
    cast = row_view(a)
    res, idx = np.unique(cast, return_index=0, return_inverse=1)
    return where_duplicate(idx)


# ====================================================================================================
def where_close_array(a, precision=3, axis=1):
    # TODO:  impliment for ndarray
    a = np.round(a, precision)
    cast = row_view(a)
    res, idx = np.unique(cast, return_index=0, return_inverse=1)
    return where_duplicate(idx)


# ====================================================================================================
def arange_like(a):
    return np.arange(len(a))


# ====================================================================================================
def multirange(*shape):
    N, dl = flatten(shape)
    return np.tile(range(dl), (N, 1))


# ====================================================================================================
# NOTE: TOO SLOW!!
# def grid_like(a):
# """create grid from the shape of the given array"""
# return shape2grid( a.shape )

# ====================================================================================================
class Grid(np.lib.index_tricks.nd_grid):
    def like(self, a):
        """create grid from the shape of the given array"""
        return self.from_shape(np.shape(a))

    @staticmethod
    def _shape_tuple(*shape):
        if len(shape) == 1:  # single argument passed - either tuple or number
            shape = shape[0]
        if isinstance(shape, int):
            shape = shape,
        return shape

    def from_shape(self, *shape):
        """Creates an index grid from shape tuple. """
        shape = self._shape_tuple(*shape)
        return self.from_ranges(np.zeros_like(shape), shape)

    def unitary(self, *shape):
        shape = self._shape_tuple(*shape)
        dim = len(shape) + 1
        norm = np.r_['0,%d,0' % dim, shape]
        return self.from_ranges(np.zeros_like(shape), shape) / norm

    def from_ranges(self, lower, upper):
        """Use index ranges to construct and index grid"""
        slices = map(slice, lower, upper)
        return self[tuple(slices)].astype(int)

        # ====================================================================================================
        # NOTE: use hstack instead
        # from recipes.iter import flatiter
        # def flatten(a):
        # """flatten arbitrarily nested iterator and return as array /TODO: masked array."""
        ##if any(map(np.ma.isMA, a)):
        ##with warnings.catch_warnings():
        # return np.fromiter(flatiter(a), float)

        # ====================================================================================================
