# std libs
import os
import sys
import pickle
import warnings
import traceback
import itertools as itt
from pathlib import Path
import mmap
# local libs
from recipes.pprint.misc import overlay
from recipes.interactive import is_interactive

from warnings import formatwarning as original_formatwarning

import itertools as itt
import glob
import json

from recipes.regex import glob_to_regex
import re
import numpy as np


FORMATS = {'json': json,
           'pkl': pickle}  # dill, sqlite
MODES = {pickle: 'b', json: ''}


BASH_BRACES = re.compile(r'(.*?)\{([^}]+)\}(.*)')

# def dumper(obj):
#     if hasattr(obj, 'to_json'):
#         return obj.to_json()
#     return obj.__dict__

# return dumps(some_big_object, default=dumper)


def guess_format(filename):
    # use filename to guess format
    ext = Path(filename).suffixes[-1].lstrip('.')
    formatter = FORMATS.get(ext, None)
    if formatter is None:
        raise ValueError(
            'Could not guess file format from filename. Please provide the '
            'expected format for deserialization of file: {filename!r}'
        )
    return formatter


def deserialize(filename, formatter=None, **kws):
    path = Path(filename)
    formatter = formatter or guess_format(path)
    with path.open(f'r{MODES[formatter]}') as fp:
        return formatter.load(fp, **kws)


def serialize(filename, data, formatter=None, **kws):
    path = Path(filename)
    if not path.parent.exists():
        path.parent.mkdir()

    formatter = formatter or guess_format(path)
    with path.open(f'w{MODES[formatter]}') as fp:
        formatter.dump(data, fp, **kws)


def load_pickle(filename, **kws):
    return deserialize(filename, pickle, **kws)


def save_pickle(filename, data, **kws):
    serialize(filename, data, pickle, **kws)


def load_json(filename, **kws):
    return deserialize(filename, json, **kws)


def save_json(filename, data, **kws):
    serialize(filename, data, json, **kws)


def iter_files(path, extensions='*', recurse=False):
    """
    Generator that yields all files in a directory tree with given file
    extension(s), optionally recursing down the directory tree

    Parameters
    ----------
    path : str or Path
        Location of the root folder. Can also be a glob pattern of
        filenames to load eg: '/path/SHA_20200715.000[1-5].fits'
    extensions : str or tuple or list
        The filename extensions to consider. All files with any of these
        extensions will be included

    Yields
    -------
    pathlib.Path
        system path pointing to the file

    Raises
    ------
    ValueError
        If the given path is not a directory
    """

    # if isinstance(path, str):
    # check if this is a wildcard
    path = str(path)
    if glob.has_magic(path):
        yield from glob.iglob(path, recursive=recurse)
        return

    path = Path(path)
    if not path.is_dir():
        raise ValueError(f"'{path!s}' is not a directory or a glob pattern")

    if isinstance(extensions, str):
        extensions = (extensions, )

    # iterate all files with given extensions
    itr = path.rglob if recurse else path.glob
    yield from itt.chain(*(itr(f'*.{ext.lstrip(".")}') for ext in extensions))


def bash_expansion(pattern):
    # handle special bash expansion syntax here  xx{12..15}.fits
    mo = BASH_BRACES.match(pattern)
    if mo:
        folder = Path(pattern).parent
        head, middle, tail = mo.groups()
        if '..' in middle:
            start, stop = map(int, middle.split('..'))
            items = range(start, stop + 1)
            # bash expansion is inclusive of both numbers in brackets
        else:
            items = middle.split(',')

        for x in items:
            yield f'{head}{x}{tail}'


def bash_contraction(items):
    if len(items) == 1:
        return items[0]

    fenced = []
    items = np.array(items)
    try:
        nrs = items.astype(int)
    except ValueError as err:
        fenced = items
    else:
        splidx = np.where(np.diff(nrs) != 1)[0] + 1
        indices = np.split(np.arange(len(nrs)), splidx)
        nrs = np.split(nrs, splidx)
        for i, seq in enumerate(nrs):
            if len(seq) == 1:
                fenced.extend(items[indices[i]])
            else:
                fenced.append(brace_range(items[0], seq))

    return brace_list(fenced)


def common_start(items):
    common = ''
    for letters in zip(*items):
        if len(set(letters)) > 1:
            break
        common += letters[0]
    return common


def brace_range(stem, seq):
    zfill = len(str(seq[-1]))
    pre = stem[:-zfill]
    sep = ',' if len(seq) == 2 else '..'
    s = sep.join(np.char.zfill(seq[[0, -1]].astype(str), zfill))
    return f'{pre}{{{s}}}'


def brace_list(items):
    if len(items) == 1:
        return items[0]

    pre = common_start(items)
    i0 = len(pre)
    s = ','.join(sorted(item[i0:] for item in items))
    return f'{pre}{{{s}}}'

# def bash_expansion_filter(pattern):
#     # handle special bash expansion syntax here  xx{12..15}.fits
#     mo = REGEX_BASH_RANGE.match(pattern)
#     if mo:
#         # special numeric sequence pattern.  Make it a glob expression.
#         head, start, stop, tail = mo.groups()
#         r = range(int(start), int(stop))
#         key = f'{head}{{{",".join(map(str, r))}}}{tail}'
#         #
#         regex = glob_to_regex(key)
#         folder = Path(pattern).parent
#         yield from filter(regex.match, map(str, folder.iterdir()))


def iter_ext(files, extensions='*'):
    """
    Yield all the files that exist with the same root and stem but different
    file extension(s)

    Parameters
    ----------
    files : Container or Iterable
        The files to consider
    extensions : str or Container of str
        All file extentions to consider

    Yields
    -------
    Path
        [description]
    """
    if isinstance(extensions, str):
        extensions = (extensions, )

    for file in files:
        for ext in extensions:
            yield from file.parent.glob(f'{file.stem}.{ext.lstrip(".")}')


def iter_lines(filename, *section, strip=os.linesep):
    """
    File line iterator for text files. Optionally return only a section of the
    file. Trailing newline character are stripped by default

    Two function signatures are accepted:
        iter_lines(filename, stop)
        iter_lines(filename, start, stop[, step])

    Parameters
    ----------
    filename : str, Path
        File system location of the file to read
    *section
        The [start], stop, [step] lines 
    strip : str, optional
        characters to strip from lines, by default system specific newline

    Yields
    -------
    str
        lines from the file
    """
    with open(str(filename), 'r') as fp:
        for s in itt.islice(fp, *(section or None, )):
            yield s.strip(strip)


def read_lines(filename, *section, strip=os.linesep, filterer=None, echo=0):
    """
    Read lines from a file given the filename.

    Parameters
    ----------
    filename : str, Path
        File system location of the file to read
    *section
        The [start], stop, [step] lines
    strip : str, optional
        characters to strip from lines, by default system specific newline
    echo : int, optional
        The number of lines from the file to flush to stdout, by default False

    Returns
    -------
    [type]
        [description]
    """
    # Read file content
    content = iter_lines(filename, *section, strip=strip)
    if filterer is not False:
        content = filter(filterer, content)

    content = list(content)

    # Optionally print the content
    if echo:
        print(show_lines(filename, content))
    return content


def show_lines(filename, lines):
    n = len(lines)
    if n:
        msg = f'Read file {filename!r} containing:'
        echo = min(echo, n)
        msg += (f'{os.linesep}\t'.join([''] + lines[:echo]))
        ndot = 3  # Number of ellipsis dots
        # TODO: tell nr omitted lines
        if n > echo:
            msg += ('.\n' * ndot)
        if n > echo + ndot:
            msg += ('\n'.join(lines[-ndot:]))
    else:
        msg = 'File %r is empty!'
    return msg


def count_lines(filename):
    """Fast line count for files"""
    filename = str(filename)  # conver path objects

    if not os.path.exists(filename):
        raise ValueError(f'No such file: {filename!r}')

    if os.path.getsize(filename) == 0:
        return 0

    with open(str(filename), 'r+') as fp:
        buf = mmap.mmap(fp.fileno(), 0)
        count = 0
        readline = buf.readline
        while readline():
            count += 1
        return count


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


def walk_level(dir_, depth=1):
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


# TODO: move to io.trace ??
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
        return self._wrap_message(self.wrapped(*args, **kws))

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
        new_stack = stack
        if is_interactive():  # and self.trim_ipython_stack:
            trigger = "exec(compiler(f.read(), fname, 'exec'), glob, loc)"
            for i, s in enumerate(stack):
                if trigger in s:
                    new_stack = ['< %i lines omitted >\n' % i] + stack[i:]
                    break

            # should now be at the position where the real traceback starts

            # when code execution is does via a magic, there is even more
            # IPython lines in the stack. Remove
            # trigger = 'exec(code_obj, self.user_global_ns, self.user_ns)'

            # when we have an embeded terminal
            triggers = 'terminal/embed.py', 'TracebackWrapper'
            done = False
            for i, s in enumerate(new_stack):
                for j, trigger in enumerate(triggers):
                    if trigger in s:
                        new_stack = new_stack[:i]
                        new_stack.append(
                            '< %i lines omitted >\n' % (len(stack) - i))
                        done = True
                        break
                if done:
                    break

            # i += 1
            # # noinspection PyRedundantParentheses
            # if (len(stack) - i):
            #     msg += '\n< %i lines omitted >\n' % (len(stack) - i)

        # last few lines in the stack are those that wrap the warning
        # message, so we filter those
        # for s in stack:

        # for s in stack[i:]:
        #     if '_showwarnmsg' in s:
        #         # last few lines in the stack are those that wrap the warning
        #         # message, so we filter those
        #         break
        #
        #     msg += s
        return ''.join(new_stack)


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
        warnings.formatwarning = original_formatwarning


if __name__ == '__main__':
    sys.stdout = TracePrints()
    print('Hello World!')
    # restore
    sys.stdout = sys.stdout.stdout

    wtb = WarningTraceback()
    warnings.warn('Dinosaurs!!')
    # restore
    wtb.off()
