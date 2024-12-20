
# std
import numbers
import tempfile
from pathlib import Path

# third-party
import numpy as np
from loguru import logger

# relative
from ..containers import ensure


def load_memmap(loc=None, shape=None, dtype=None, fill=None, masked=False,
                overwrite=False, **kws):
    """
    Pre-allocate a writeable shared memory map as a container for the results of
    (parallel) computation. This is a wrapper around `np.lib.format.open_memmap`
    with a more convenient API for our purposes here. For example, if file
    already exists and `overwrite` is False, so that the file is opened in
    update mode, `fill` parameter will be ignored.

    Parameters
    ----------
    loc : str or path-like, optional
        File location, by default None, which defaults to the sysem temporary
        storage location via the `tempfile` package.
    shape : tuple of int, optional
        Desired shape of the array, by default None. Shape will be read from the
        file if loading an exisiting memmap, ignoring this parameter.
    dtype : data-type, optional
        Desired data type for array, by default None. Ignored when reading from
        exisiting memmap. Can be omitted when creating an array and providing a
        `fill` value.
    fill : object, optional
        Item used to populate the array when creating, by default None. The
        array dtype will be decided based on this value  if not provided.
    masked: bool, optional
        Whether or not to create a mask for data censoring (also a memmory map).
        If True, a second memmory map with boolean data type, having the same
        shape as the data array is created. The returned object is then a
        `np.ma.MaskedArray` instance that has the ``.data`` and ``.mask`
        attributes as the respective `np.memmap`s.
    overwrite : bool, optional
        Whether to overwrite an existing file, by default False.

    Returns
    -------
    numpy.memmap
        Memmory mapped array.

    Raises
    ------
    ValueError
        If requested shape does not match exisiting memmap shape and overwrite
        is False.
    """
    data = _load_memmap(loc, shape, dtype, fill, overwrite, **kws)

    if masked:
        mask = _load_memmap(loc, shape, bool, True, overwrite, '.mask.npy', **kws)
        return np.ma.MaskedArray(data, mask, copy=False)

    return data


def _load_memmap(loc=None, shape=None, dtype=None, fill=None, overwrite=False, 
                 ext='.npy', **kws):

    # NOTE: Objects created by this function have no synchronization primitives
    #  in place. Having concurrent workers write on overlapping shared memory
    #  data segments, for instance by using inplace operators and assignments on
    #  a numpy.memmap instance, can lead to data corruption since numpy does not
    #  offer atomic operations. We do not risk that issue if each process is
    #  updating an exclusive segment of the shared result array.

    if loc is None:
        _fid, loc = tempfile.mkstemp(ext)
        overwrite = True  # FIXME. messages below will be inaccurate

    loc = Path(loc)
    filename = str(loc)
    folder = loc.parent

    # create folder if needed
    if not folder.exists():
        logger.info('Creating folder: {!r:}.', str(folder))
        folder.mkdir(parents=True)

    if shape:
        shape = ensure.tuple(shape)

    # update mode if existing file, else read
    new = not loc.exists() or overwrite
    if new:
        mode = 'w+'  # FIXME w+ r+ same??
        # default dtype for writing
        dtype = dtype or (float if fill is None else type(fill))

        logger.debug('Creating memmap of shape {!s} and dtype {!r:} at {!r:}.',
                     shape, dtype, filename)
    else:
        mode = 'r+'
        logger.debug('Loading memmap at {!r:}.', filename)

    # create memmap
    # NOTE: using ` np.lib.format.open_memmap` here so that we get a small
    #  amount of header info for easily loading the array
    data = np.lib.format.open_memmap(filename, mode, dtype, shape, **kws)

    # check shape and dtype match
    if dtype:
        dtype = np.dtype(dtype)

    for what, val in dict(shape=shape, dtype=dtype).items():
        if val and val != (dval := getattr(data, what)):
            raise ValueError(
                f'Loaded memmap has {what}:\n    {dval}\nwhich is different to '
                f'that requested:\n    {val}.\nOverwrite: {overwrite}.'
            )

    # overwrite data
    if new and (fill is not None):
        logger.opt(lazy=True).debug(
            'Overwriting memory map data with input {}.',
            lambda: fill if isinstance(fill, numbers.Number) else 'data')

        data[:] = fill

    return data


def load_memmap_nans(loc=None, shape=None, dtype=None, overwrite=False, **kws):
    return load_memmap(loc, shape, dtype, fill=np.nan, overwrite=overwrite, **kws)


# ---------------------------------------------------------------------------- #
