import itertools as itt
import os
import pickle
import sys
import traceback
import warnings
from pathlib import Path

import motley


# ===============================================================================
def load_pickle(filename):
    with Path(filename).open('rb') as fp:
        return pickle.load(fp)


def save_pickle(filename, data):
    with Path(filename).open('wb') as fp:
        pickle.dump(data, fp)


# ===============================================================================
def note(msg):
    """colourful notes"""
    colour, style = 'g', 'bold'
    w = motley.codes.apply('NOTE:', colour, style)
    print('{} {}'.format(w, msg))


def warn(warning):
    """colourful warnings"""
    colour, style = 'yellow', 'bold'  # 202
    w = motley.codes.apply('WARNING:', colour, style)
    print('{} {}'.format(w, warning))


# ===============================================================================
def iocheck(instr, check, raise_error=0, convert=None):
    """
    Tests a input str for validity by calling the provided check function on it.
    Returns None if an error was found or raises ValueError if raise_error is set.
    Returns the original list if input is valid.
    """
    if not check(instr):
        msg = 'Invalid input!! %r \nPlease try again: ' % instr  # REPITITION!!!!!!!!!!!!
        if raise_error == 1:
            raise ValueError(msg)
        elif raise_error == 0:
            print(msg)
            return
        elif raise_error == -1:
            return
    else:
        if convert:
            return convert(instr)
        return instr


# ===============================================================================
def read_file_slice(filename, *which):
    """
    Read a slice of lines from a file.

    read_file_slice(filename, stop)
    read_file_slice(filename, start, stop[, step])
    """
    # Parameters
    # ----------
    # filename : str
    # Path to file from which to read data

    # """
    with open(str(filename), 'r') as fp:
        return list(itt.islice(fp, *which))
        # TODO: optionally return the generator


def read_file_line(filename, n):
    # NOTE: essentially the same as linecache.getline(filename, n)
    with open(str(filename), 'r') as fp:
        return next(itt.islice(fp, n, n + 1))


def read_data_from_file(filename, n=None, remove_blank=True, echo=False):
    """
    Read lines from a file given the filename.
    Parameters
    ----------
    n: int
        number of lines to read
    remove_blank: strip empty lines
    echo        : the number of lines from the file to flush to stdout
    """
    # Read file content
    with open(str(filename), 'r') as fp:
        chunk = itt.islice(fp, n)
        content = map(lambda s: s.strip(os.linesep), chunk)  # strip newlines
        if remove_blank:
            content = filter(None, content)  # filters out empty lines [s for s in fp if s]
        content = list(content)  # create the content list from the filter

    # Optionally print the content
    if echo:
        if not len(content):
            msg = 'File %r is empty!'
        else:
            msg = 'Read file %r containing:' % filename
            echo = min(echo, len(content))
            to_print = content[:echo]
            msg += ('\n\t'.join([''] + to_print))

            ndot = 3  # Number of ellipsis dots
            if len(content) > echo:
                msg += ('.\n' * ndot)
            if len(content) > echo + ndot:
                msg += ('\n'.join(content[-ndot:]))
        print(msg)
    return content


def linecounter(filename):
    """A fast line count for files."""
    # print( 'Retrieving line count...' )
    import mmap
    with open(str(filename), "r+") as fp:
        buf = mmap.mmap(fp.fileno(), 0)
        count = 0
        readline = buf.readline
        while readline():
            count += 1
        return count


def walklevel(dir_, depth=1):
    """
    Walk the system path, but only up to the given depth
    """
    # http://stackoverflow.com/a/234329/1098683

    dir_ = dir_.rstrip(os.path.sep)
    assert os.path.isdir(dir_)

    num_sep = dir_.count(os.path.sep)
    for root, dirs, files in os.walk(dir_):
        yield root, dirs, files
        num_sep_here = root.count(os.path.sep)
        if num_sep + depth <= num_sep_here:
            del dirs[:]


from recipes.string import overlay  # , banner


class Tracer(object):
    _txtwidth = 80

    def __init__(self, active=True, banner=True):
        self.stdout = sys.stdout
        # self.original = original
        self._active = bool(active)
        self.banner = bool(banner)
        self.pre, self.post, self.pre_tb, self.post_tb = ('', '', '', '')

        if self.banner:
            name = self.__class__.__name__.join('  ')
            tw = self._txtwidth
            self.pre = overlay(name, '=' * tw, '^')
            self.post = ('=' * tw)

            self.pre_tb = overlay('Traceback ', '-' * tw, '^')
            self.post_tb = ('-' * tw)

    def _wrap_message(self, msg):
        # make banner
        return os.linesep.join((self.pre, msg, self._wrap_tb(), self.post))

    def _wrap_tb(self):
        tb = ''.join(traceback.format_stack())
        return os.linesep.join((self.pre_tb, tb, self.post_tb))

    def on(self):
        self._active = True
        # self.write = self._write

    def off(self):
        self._active = False


class TracePrints(Tracer):  # TODO: as context wrapper
    """
    Class that can be used to find print statements in unknown source code

    Examples
    --------
    >>> sys.stdout = TracePrints()
    >>> print("I am here")
    """

    def __init__(self, active=True, banner=True):
        # self.stdout = sys.stdout
        Tracer.__init__(self, active, banner)
        # self._write = self.wrap_banner(self.stdout.write, False, self.stdout)
        # set active
        (self.off, self.on)[self._active]()

        # self._write = self.wrap_banner(self.stdout.write)

    def write(self, s):
        # print() statements usually involve two calls to stdout.write
        # first to write the content, second to write a newline if we are
        # writing newline, skip the banner
        if (not self._active) or (s == os.linesep):
            self.stdout.write(s)
            return

        self.stdout.write(self._wrap_message(s))

    def flush(self):
        self.stdout.flush()


class WarningTraceback(Tracer):
    """
    Class that help to track down warning statements in unknowns source code
    """

    def __init__(self, active=True, banner=True):
        """
        Activate full tracebacks for warnings

        Parameters
        ----------
        active
        banner

        Examples
        --------
        >>> import warnings
        >>> from recipes.io.utils import WarningTraceback

        >>> wtb = WarningTraceback()
        >>> warnings.warn('Dinosaurs!')
        ------------------------------- WarningTraceback -------------------------------
        /usr/local/lib/python3.5/dist-packages/ipykernel_launcher.py:5: UserWarning: Dinosaurs!
          File "/usr/lib/python3.5/runpy.py", line 193, in _run_module_as_main
            "__main__", mod_spec)
        ...
          File "/usr/lib/python3.5/warnings.py", line 18, in showwarning
            file.write(formatwarning(message, category, filename, lineno, line))
        --------------------------------------------------------------------------------
        >>> wtb.off()
        >>> warnings.warn('Dinosaurs!')
        /usr/local/lib/python3.5/dist-packages/ipykernel_launcher.py:1: UserWarning: Dinosaurs!
          Entry point for launching an IPython kernel.
        """
        # backup original warning formatter
        self.original = warnings.formatwarning
        Tracer.__init__(self, active, banner)
        # self._write = self.wrap_banner(self.original, True, self.stdout)
        # set active
        (self.off, self.on)[self._active]()

    def _formatwarning(self, *args, **kws):
        # make banner
        return self._wrap_message(self.original(*args, **kws)) + os.linesep

    def on(self):
        self._active = True
        warnings.formatwarning = self._formatwarning

    def off(self):
        self._active = False
        warnings.formatwarning = self.original


if __name__ == '__main__':
    sys.stdout = TracePrints()
    print('Hello World!')
    # restore
    sys.stdout = sys.stdout.stdout

    wtb = WarningTraceback()
    warnings.warn('Dinosaurs!!')

    # from IPython import embed
    # sys.stdout = sys.stdout.stdout
    # embed()
