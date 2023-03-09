
# std
import numbers
import tempfile
from pathlib import Path

# third-party
import numpy as np
from loguru import logger

# relative
from ..oo import coerce


def load_memmap(loc=None, shape=None, dtype=None, fill=None, overwrite=False):
    """
    Pre-allocate a writeable shared memory map as a container for the results of
    parallel computation. If file already exists and overwrite is False open in
    update mode and fill will be ignored. Data persistence ftw.
    """

    # NOTE: Objects created by this function have no synchronization primitives
    #  in place. Having concurrent workers write on overlapping shared memory
    #  data segments, for instance by using inplace operators and assignments on
    #  a numpy.memmap instance, can lead to data corruption since numpy does not
    #  offer atomic operations. We do not risk that issue if each process is
    #  updating an exclusive segment of the shared result array.

    if loc is None:
        _fid, loc = tempfile.mkstemp('.npy')
        overwrite = True  # fixme. messages below will be inaccurate

    loc = Path(loc)
    filename = str(loc)
    folder = loc.parent

    # create folder if needed
    if not folder.exists():
        logger.info('Creating folder: {!r:}', str(folder))
        folder.mkdir(parents=True)

    # update mode if existing file, else read
    new = not loc.exists()
    mode = 'w+' if (new or overwrite) else 'r+'  # FIXME w+ r+ same??
    if dtype is None:
        dtype = 'f' if fill is None else type(fill)

    # create memmap
    shape = coerce(shape, tuple, numbers.Integral) if shape else None
    if new:
        logger.debug('Creating memmap of shape {!s} and dtype {!r:} at {!r:}.',
                     shape, dtype, filename)
    else:
        logger.debug('Loading memmap at {!r:}.', filename)

    # NOTE: using ` np.lib.format.open_memmap` here so that we get a small
    #  amount of header info for easily loading the array
    data = np.lib.format.open_memmap(filename, mode, dtype, shape)

    if data.shape != shape:
        raise ValueError(f'Loaded memmap has shape {data.shape}, which is '
                         f'different to that requested: {shape}. Overwrite: '
                         f'{overwrite}.')

    # overwrite data
    if (new or overwrite) and (fill is not None):
        logger.debug('Overwriting data with {:g}.', fill)
        data[:] = fill

    return data


def load_memmap_nans(loc, shape=None, dtype=None, overwrite=False):
    return load_memmap(loc, shape, dtype, fill=np.nan, overwrite=overwrite)


# ---------------------------------------------------------------------------- #
