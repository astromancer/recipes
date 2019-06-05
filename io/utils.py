
# std libs
import os
import sys
import pickle
import warnings
import traceback
import itertools as itt
from pathlib import Path

# local libs
import motley
from recipes.pprint import overlay
from recipes.interactive import is_interactive



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
        msg = 'Invalid input!! %r \nPlease try again: ' % instr
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
            # filters out empty lines [s for s in fp if s]
            content = filter(None, content)

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


# class Singleton(object):
#     # source
#     # https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html
#     class __Singleton:
#         def __init__(self, arg):
#             self.val = arg
#
#         def __str__(self):
#             return repr(self) + self.val
#
#     instance = None
#
#     def __init__(self, arg):
#         if Singleton.instance is None:
#             Singleton.instance = Singleton.__Singleton(arg)
#         else:
#             Singleton.instance.val = arg
#
#     def __getattr__(self, name):
#         return getattr(self.instance, name)
# #
# Singleton/BorgSingleton.py
# Alex Martelli's 'Borg'

# class Borg:
#     _shared_state = {}
#
#     def __init__(self):
#         self.__dict__ = self._shared_state
#
#
# class Singleton(Borg):
#     def __init__(self, arg):
#         Borg.__init__(self)
#         self.val = arg
#
#     def __str__(self):
#         return self.val


# from recipes.oo.meta import SingletonMetaClass

class MessageWrapper(object):

    def __init__(self, wrapped, title=None, width=80, char='='):
        self.active = True

        if isinstance(wrapped, MessageWrapper):
            # avoid wrapping multiple times !!!
            self.wrapped = wrapped.wrapped
        else:
            self.wrapped = wrapped

        # get the class name and pad with single whitespace on each side
        title = self.get_title(title)
        self.width = int(width)
        self.pre = os.linesep + overlay(title, char * self.width, '^')
        self.post = (char * self.width)

    def __call__(self, *args, **kws):
        return self._wrap_message(
                self.wrapped(*args, **kws))

    def get_title(self, title):
        if title is None:
            title = self.__class__.__name__
        return title.join('  ')

    def _wrap_message(self, msg):
        if self.active:
            # make banner
            return os.linesep.join((self.pre,
                                    msg,
                                    self.post))
        else:
            return msg

    def on(self):
        self.active = True

    def off(self):
        self.active = False


class TracebackWrapper(MessageWrapper):
    """
    Base class for printing and modifying stack traceback
    """
    trim_ipython_stack = True

    def __init__(self, title='Traceback', width=80, char='-'):
        super().__init__(self._format_stack, title, width, char)

    def _format_stack(self):
        stack = traceback.format_stack()
        # if we are in IPython, we do't actually want to print the entire
        # stack containing all the IPython code execution boilerplate noise,
        # so we filter all that crap here
        msg = ''
        i = 0
        if is_interactive() and self.trim_ipython_stack:
            trigger = 'exec(code_obj, self.user_global_ns, self.user_ns)'
            enum_stack = enumerate(stack)
            for i, s in enum_stack:
                if trigger in s:
                    break

            # when code execution is does via a magic, there is even more
            # IPython boilerplate to remove
            trigger = "exec(compiler(f.read(), fname, 'exec'), glob, loc)"
            for i, s in enum_stack:
                if trigger in s:
                    break

            i += 1
            msg = '< %i lines omitted >\n\n' % i
            # msg += '\n\n'

        for s in stack[i:]:
            if '_showwarnmsg' in s:
                # last few lines in the stack are those that wrap the warning
                # message, so we filter those
                break

            msg += s

        return msg


class TracePrints(MessageWrapper):
    # TODO: as context wrapper : see contextlib.redirect_stdout
    """
    Class that can be used to find print statements in unknown source code

    Examples
    --------
    >>> sys.stdout = TracePrints()
    >>> print("I am here")
    """

    def __init__(self, title=None, width=80, char='='):
        super().__init__(lambda s: s, title, width, char)
        self.format_stack = TracebackWrapper()
        self.stdout = sys.stdout

    def _wrap_message(self, msg):
        return super()._wrap_message(
                os.linesep.join((msg, self.format_stack())))

    def write(self, s):
        # print() statements usually involve two calls to stdout.write
        # first to write the content, second to write a newline if we are
        # writing newline, skip the banner
        if (not self.active) or (s == os.linesep):
            self.stdout.write(s)
        else:
            self.stdout.write(self(s))

    def flush(self):
        self.stdout.flush()


class WarningTraceback(MessageWrapper):
    """
    Class that help to track down warning statements in unknowns source code
    """

    # if warnings.formatwarning is self._formatwarning

    # from warnings import formatwarning
    # original = formatwarning

    def __init__(self, title=None, width=80, char='='):
        """
        Activate full traceback for warnings

        Parameters
        ----------

        Examples
        --------
        >>> wtb = WarningTraceback()
        >>> warnings.warn('Dinosaurs!')
        # TODO: generate this output dynamically ???

        ------------------------------- WarningTraceback -------------------------------
        /usr/local/lib/python3.5/dist-packages/ipykernel_launcher.py:5: UserWarning: Dinosaurs!
          File "/usr/lib/python3.5/runpy.py", line 193, in _run_module_as_main
            "__main__", mod_spec)
        ... <some lines omitted for brevity>
          File "/usr/lib/python3.5/warnings.py", line 18, in showwarning
            file.write(formatwarning(message, category, filename, lineno, line))
        --------------------------------------------------------------------------------

        >>> wtb.off()
        >>> warnings.warn('Dinosaurs!')
        /usr/local/lib/python3.5/dist-packages/ipykernel_launcher.py:1: UserWarning: Dinosaurs!
          Entry point for launching an IPython kernel.
        """

        super().__init__(warnings.formatwarning, title, width, char)
        self.format_stack = TracebackWrapper()
        self.on()

    def _wrap_message(self, msg):
        return super()._wrap_message(
                os.linesep.join((msg, self.format_stack())))

    def on(self):
        self.active = True
        warnings.formatwarning = self

    def off(self):
        self.active = False
        warnings.formatwarning = self.wrapped


if __name__ == '__main__':
    sys.stdout = TracePrints()
    print('Hello World!')
    # restore
    sys.stdout = sys.stdout.stdout

    wtb = WarningTraceback()
    warnings.warn('Dinosaurs!!')
    # restore
    wtb.off()
