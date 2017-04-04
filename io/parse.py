import os
import glob
from functools import partial
from collections import Callable

from .utils import warn, iocheck, read_data_from_file
from ..set import OrderedSet


def resolver(givenpath, input_):
    """Resolves relative paths etc. """
    # interpret the path which is attached to the input as relative to givenpath
    # 'filename' might be a directory/glob/filename of text list/actual filename
    # returns the path in which data is to be read, as well as with the expression to be read
    # including the path
    path, filename = os.path.split(input_)
    path = os.path.realpath(os.path.join(givenpath, path))
    return path, os.path.join(path, filename)


def absolute_paths(path, data):
    ndata = []
    for d in data:
        p, n = os.path.split(str(d))
        if not p:
            d = os.path.join(path, n)
        ndata.append(d)
    return ndata


# def converter(data):
#     if isinstance(convert, Callable):
#         return list(map(convert, data))
#     else:
#         return data

#         # else:
#         # raise TypeError( ('type {} is not callable.'
#         # 'convert argument should be a callable type.'
#         # ).format(type(convert)) )


def excluder(exclude, data, path):
    if exclude:
        # exclude=None avoids infinite recursion
        exclude = to_list(exclude, path=path, exclude=None, convert=None)
        return list(OrderedSet(data) - OrderedSet(exclude))
    else:
        return data


def to_list(data, check=None, **kws):
    # TODO: TESTS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # TODO: pass in raise message?
    # FIXME: single filename containing text intended as sole input is ambiguous since its contents
    # FIXME: will be read. This may cause problems, especially with binary files.
    # FIXME: consider flagging text lists with a @
    """
    Test a list input values for validity by calling check on each value in the list.
    Parameters
    ----------
    data : str
        One of the following: * a single filename
                              * a list of file names
                              * a directory name
                              * name of file containing a list of the input items
                              * file glob expression eg: '*.fits'
    check : callable
        function to call as a validity test.  Defaults to lambda x: True

    Keywords
    --------
    max_check : int
        Maximum number of inputs to run check on.
    readlines :
        Number of lines to read from the file. Read all lines if unspecified.
    include :
        Only files with these extensions will be read. Essentially a filter. Necessary when
        data might be a single file with known extension.  If include is not specified, this
        function will erroneously try read the list of filenames from it.
    exclude :
        File extensions/names to exclude.
    raise_error : bool
        Whether to raise error when file is invalid according to check.
    path : str
        Path to prepend to input when trying to interpret.  This can be a relative path.
    abspath : bool
        whether absolute or relative paths should be returned.

    Returns
    -------
    data : {list, None}
        The filtered data if input is valid
        OR
        None for invalid data (according to check) if raise_error is not set.

    Raises
    ------
    IOError
        for invalid input (according to check) if raise_error is set.

    Examples
    --------
    """

    if data is None:
        return  # Null object pattern

    trivial = lambda x: True
    check = check or trivial
    raise_error = kws.get('raise_error', 0)
    max_check = kws.get('max_check', 100)
    readlines = kws.get('readlines')
    include = kws.get('include', '*.fits')
    exclude = kws.get('exclude', '.*')  # hidden files ignored by default
    givenpath = kws.get('path', '')
    givenpath = str(givenpath)
    abspath = kws.get('abspath', True)
    convert = kws.get('convert', None)
    sort = kws.get('sort', True)

    if not (convert is None or isinstance(convert, Callable)):
        raise TypeError('convert must be a callable')

    if isinstance(data, str):
        data = [data]

    # Read
    if len(data) == 1:
        path, toread = resolver(givenpath, data[0])

        # if input is directory
        if os.path.isdir(toread):
            # logging.debug('Input DIRECTORY: %s' %toread)
            # list all (non-hidden) files in the directory with given extension
            # path, _, data = next(os.walk(toread))
            # data = [fn for fn in data if fn.endswith(include)]  # only files
            if glob.has_magic(include):
                return to_list(os.path.join(toread, include),
                               check,
                               path=givenpath,
                               exclude=exclude,
                               raise_error=raise_error)
                               # check=check)

            else:
                raise ValueError('include must be glob expression. received %s' % include)

        # if input is glob
        elif glob.has_magic(toread):  # if the input is a glob expression
            data = glob.glob(toread)

        # if input is a str is intended to be read as a text file containing the actual data
        elif os.path.split(toread)[-1].startswith('@'):
            try:
                data = read_data_from_file(toread, readlines)
            except IOError:
                msg = 'Invalid filename list: %s' % data[0]
                if raise_error:
                    raise IOError(msg)
                else:
                    print(msg)
                    return
        else:  # single filename given
            data = [toread]
            # path = givenpath or os.path.split( data[0] )[0]
    else:
        _resolver = partial(resolver, givenpath)
        paths, data = zip(*map(_resolver, data))
        path = paths[0]

    # Filter
    data = excluder(exclude, data, givenpath)

    # Convert
    if convert:
        data = list(map(convert, data))     # converter(data)

    # try:
    if abspath:
        data = absolute_paths(path, data)
        # except Exception as err:
        # from IPython import embed
        # embed()

    # Check
    i = 0
    badnames = []
    while i < len(data):
        nm = data[i]
        if not iocheck(nm, check, raise_error):
            badnames.append(nm)
        i += 1
        if i >= max_check and not check is trivial:
            warn('The input list is too long. '
                 'Skipping remaining validity checks\n')
            break

    # Sort
    if len(badnames):
        return              #TODO: or raise???

    if sort:
        return sorted(data)

    return data


# Alias
# parselist = parseto_list

if __name__ == '__main__':
    # TODO: unit tests
    # parseto_list()
    print('TODO: unit tests')



#===============================================================================
#io.parse.to_list??????
# class parse():
#
#     #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     @staticmethod
#     #@path.to_string.kw('path')
#     def read(data, check=None, **kws):
#         if isinstance(data, str):
#             data = [data]
#
#         # Read
#         if len(data)==1:         #and not data[0].endswith('.fits')
#             path, toread = resolver( data[0] )
#
#             #if input is directory
#             if os.path.isdir(toread):
#                 #list all the (non-hidden) files with given extension
#                 path, _, data = next(os.walk(toread))
#                 data = [fn for fn in data if fn.endswith(include)]
#
#             #if input is glob
#             elif glob.has_magic(toread):     #if the input is a glob expression
#                 data = glob.glob(toread)
#
#             #if input is a str not matching include expression. i.e not intended single as single file
#             elif not data[0].endswith( include ):                         #if the input is a text list with filenames
#                 try:
#                     data = read_data_from_file( toread, readlines )
#
#                 except IOError:
#                     msg = 'Invalid filename list: %s' %data[0]
#                     if raise_error:
#                         raise IOError( msg )
#                     else:
#                         print( msg )
#                         return
#             else:                                                           #single filename given
#                 data = [toread]
#                 #path = givenpath or os.path.split( data[0] )[0]
#         else:
#             paths, data = zip( *map(resolver, data) )
#             path = paths[0]
#
#     #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def resolver( thing ):
#         #interpret the path which is attached to the input as relative to givenpath
#         path, filename = os.path.split( thing )       #here 'filename' might be a directory/glob/filename of text list/actual filename
#         path = os.path.realpath( os.path.join(givenpath, path) )
#         return path, os.path.join( path, filename )
#
#     #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def to_list(self, check=None, **kws):
#         return parseto_list(data, check=None, **kws)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

