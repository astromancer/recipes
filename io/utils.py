
import os
import pickle
import itertools as itt
from pathlib import Path

from ansi.str import as_ansi


#===============================================================================
def load_pickle(filename):
    with Path(filename).open('rb') as fp:
        return pickle.load(fp)


def save_pickle(filename, data):
    with Path(filename).open('wb') as fp:
        pickle.dump(data, fp)

#===============================================================================
def note(msg):
    colour, style = 'g', 'bold'
    w = as_ansi('NOTE:', (colour, style))
    print('{} {}'.format(w, msg))

def warn(warning):
    """colourful warnings"""
    colour, style = 'yellow', 'bold' # 202
    w = as_ansi('WARNING:', (colour, style))
    print('{} {}'.format(w, warning))

#===============================================================================
def iocheck(instr, check, raise_error=0, convert=None):
    """
    Tests a input str for validity by calling the provided check function on it.
    Returns None if an error was found or raises ValueError if raise_error is set.
    Returns the original list if input is valid.
    """
    if not check(instr):
        msg = 'Invalid input!! %r \nPlease try again: ' %instr                                              #REPITITION!!!!!!!!!!!!
        if raise_error==1:
            raise ValueError(msg)
        elif raise_error==0:
            print(msg)
            return
        elif raise_error==-1:
            return
    else:
        if convert:
            return convert(instr)
        return instr

#===============================================================================
def read_file_slice(filename, *which):
    """
    Read a slice of lines from a file.

    read_file_slice(filename, stop)
    read_file_slice(filename, start, stop[, step])
    """
    #Parameters
    #----------
    #filename : str
        #Path to file from which to read data

    #"""
    with open(str(filename), 'r') as fp:
        return list(itt.islice(fp, *which))     #TODO: optionally return the generator

#===============================================================================
def read_file_line(filename, n):    #NOTE: essentially the same as linecache.getline(filename, n)
    with open(str(filename), 'r') as fp:
        return next(itt.islice(fp, n, n+1))

#===============================================================================
def read_data_from_file(filename, N=None, pr=False):
    """
    Read lines from a file given the filename.
    Parameters
    ----------
    N           : number of lines to read
    pr          : whether to print the read lines
    """
    # Read file content
    with open(str(filename), 'r') as fp:
        if N:
            fp = itt.islice(fp, N)
        content = map(lambda s: s.strip(os.linesep), fp)      #strip newlines
        content = filter(None, content)                         #filters out empty lines [s for s in fp if s]
        content = list(content)                                 #create the content list from the filter

    # Optionally print the content
    MAX_LS = 25                                                 #Maximum number of lines to print
    if pr:
        ndot = 3                                                #Number of ellipsis dots
        ls_trunc = content[:MAX_LS-ndot] if len(content) > MAX_LS else content
        msg = ('You have input the txt file {} containing the following:\n{}'
               '').format(repr(filename), '\n'.join(ls_trunc))
        print(msg)
        if len(content) > MAX_LS:
            print('.\n'*3)
        if len(content) > MAX_LS+ndot:
            print('\n'.join(content[-ndot:]))

    return content


#===============================================================================
def linecounter(filename):
    """A fast line count for files."""
    #print( 'Retrieving line count...' )
    import mmap
    with open(str(filename), "r+") as fp:
        buf = mmap.mmap(fp.fileno(), 0)
        count = 0
        readline = buf.readline
        while readline():
            count += 1
        return count

