# std libs
from ..functionals import echo0
from contextlib import contextmanager
from recipes.string import sub
import os
from recipes.bash import brace_expand_iter
from recipes.string.brackets import braces
import docsplice as doc

import pickle

import itertools as itt
from pathlib import Path
import mmap
# local libs
# from recipes.string import overlay
# from recipes.interactive import is_interactive

import itertools as itt
import glob
import json
import shutil
import tempfile


FORMATS = {'json': json,
           'pkl': pickle}  # dill, sqlite
FILEMODES = {pickle: 'b', json: ''}


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
    with path.open(f'r{FILEMODES[formatter]}') as fp:
        return formatter.load(fp, **kws)


def serialize(filename, data, formatter=None, **kws):
    """
    Data serialization wrapper that outputs to either json or native pickle
    formats.

    Parameters
    ----------
    filename : str, Path
        [description]
    data : object
        [description]
    formatter : module {json, pickle}, optional
        If formatter argument is not explicitly provided (default), it is chosen
        based on the extension of the input filename.
    """
    path = Path(filename)
    if not path.parent.exists():
        path.parent.mkdir()

    formatter = formatter or guess_format(path)
    with path.open(f'w{FILEMODES[formatter]}') as fp:
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
    extension(s), optionally recursing down the directory tree. Brace expansion
    syntax from bash is supported, allowing multiple directory trees to be
    traversed with a single statement.

    Parameters
    ----------
    path : str or Path
        Location of the root folder. Can also be a glob pattern of
        filenames to load eg: '/path/SHA_20200715.000[1-5].fits'
        Pattern can also contain brace expansion patterns
        '/path/SHA_202007{15..18}.000[1-5].fits' in which case all valid
        files and directories in the range will be traversed.
    extensions : str or tuple or list
        The filename extensions to consider. All files with any of these
        extensions will be included. The same functionality as is provided by
        this parameter can be acheived by including the list of file extensions
        in the expansion pattern. eg: '/path/*.{png,jpg}' will get all png and
        jpg files from path directory.

    Examples
    --------
    >>> iter_files()

    Yields
    -------
    pathlib.Path
        system path pointing to the file

    Raises
    ------
    ValueError
        If the given path is not a directory
    """

    path = str(path)

    # handle brace expansion first
    special = bool(braces.match(path, False, must_close=True))
    wildcard = glob.has_magic(path)  # handle glob patterns
    if special | wildcard:
        itr = (brace_expand_iter(path) if special else
               glob.iglob(path, recursive=recurse))
        for path in itr:
            yield from iter_files(path, extensions, recurse)
        return

    path = Path(path)
    if path.is_dir():
        # iterate all files with given extensions
        if isinstance(extensions, str):
            extensions = (extensions, )

        extensions = f'{{{",".join((ext.lstrip(".") for ext in extensions))}}}'
        yield from iter_files(
            f'{path!s}/{"**/" * recurse}*.{extensions}', recurse=recurse)
        return

    if not path.exists():
        raise ValueError(f"'{path!s}' is not a directory or a glob pattern")

    # break the recurrence
    yield path


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


def iter_lines(filename, *section, mode='r', strip=None):
    """
    File line iterator for text files. Optionally return only a section of the
    file. Trailing newline character are stripped by default.

    Two basic function signatures are accepted:
        iter_lines(filename, stop)
        iter_lines(filename, start, stop[, step])

    Parameters
    ----------
    filename : str, Path
        File system location of the file to read
    *section
        The [start], stop, [step] lines.
    mode : str
        Mode used for opening files, by default r
    strip : str, optional
        Characters to strip from lines. The default value depends on the `mode`
        parameter. For text mode ('r', 'rt'), strip '\\n', for binary mode
        ('b'), strip system specific newlines. Note that python automatically
        translates system specific newlines in the file to '\\n', for files
        opened in text mode. Use `strip=''` or `strip=False` to leave lines
        unmodified.

    Examples
    --------
    >>>

    Yields
    -------
    str
        lines from the file
    """

    # note python automatically translate system newlines to '\n' for files
    # opened in text mode, but not in binary mode:
    #   https://stackoverflow.com/a/38075790/1098683
    if strip is None:
        strip = os.linesep
    strip = strip or ''
    if 'b' in mode and isinstance(strip, str):
        strip = strip.encode()

    with open(str(filename), mode) as fp:
        for s in itt.islice(fp, *(section or (None, ))):
            yield s.strip(strip)


@doc.splice(iter_lines)
def read_lines(filename, *section, mode='r', strip=None, filtered=None,
               echo=False):
    """
    Read a subset of lines from a given file.

    {Extended Summary}

    {Parameters}
    filtered : callable or None, optional
        A function that will be used to filter out unwnated lines. Filtering
        occurs after stripping unwanted characters. The default behaviour
        (filtered=None) removed all blank lines from the results.
    echo : bool, optional
        Whether to print a summary of the read content to stdout,
        by default False

    Returns
    -------
    list of str
        Lines from the file
    """
    # Read file content
    content = iter_lines(filename, *section, mode=mode, strip=strip)
    if filtered is not False:
        content = filter(filtered, content)
    content = list(content)

    # Optionally print the content
    if echo:
        print(_show_lines(filename, content))
    return content


def read_line(filename, nr, mode='r', strip=None):
    return next(iter_lines(filename, nr, nr + 1,
                           mode=mode, strip=strip))


def _show_lines(filename, lines, n=10, dots='.\n' * 3):
    """Create message for `read_lines`"""

    n_lines = len(lines)
    n = min(n, n_lines)
    if n_lines and n:
        msg = (f'Read file {filename!r} containing:'
               f'\n\t'.join([''] + lines[:n]))
        # Number of ellipsis dots (one per line)
        ndot = dots.count('\n')
        # TODO: tell nr omitted lines
        if n_lines > n:
            msg += ('.\n' * ndot)
        if n_lines > n + ndot:
            msg += ('\n'.join(lines[-ndot:]))
    else:
        msg = f'File {filename!r} is empty!'
    return msg


def count_lines(filename):
    """Fast line count for files"""
    filename = str(filename)  # conver path objects

    if not os.path.exists(filename):
        raise ValueError(f'No such file: {filename!r}')

    if os.path.getsize(filename) == 0:
        return 0

    with open(str(filename), 'r+') as fp:
        count = 0
        buffer = mmap.mmap(fp.fileno(), 0)
        while buffer.readline():
            count += 1
        return count


def write_lines(stream, lines, eol='\n'):
    """
    Write multiple lines to a file-like output stream

    Parameters
    ----------
    stream : [type]
        File-like object
    lines : iterable
        Sequence of lines to be written to the stream.
    eol : str, optional
        End-of-line character to be appended to each line, by default ''.
    """
    assert isinstance(eol, str)
    append = str.__add__ if eol else echo0

    for line in lines:
        stream.write(append(line, eol))


@contextmanager
def backed_up(filename, mode='w', backupfile=None, exception_hook=None):
    """
    Context manager for doing file operations under backup. This will backup
    your file before any read / writes are attempted. If something goes terribly
    wrong during the attempted operation, the original content will be restored.


    Parameters
    ----------
    filename : str or Path
        The file to be edited.
    mode : str, optional
        File mode for opening, by default 'w'.
    backupfile : str or Path, optional
        Location of the backup file, by default None. The default location will
        is the temporary file created by `tempfile.mkstemp`, using the prefix
        "backup." and suffix being the original `filename`.
    exception_hook : callable, optional
        Hook to run on the event of an exception if you wish to modify the
        error message. The default, None, will leave the exception unaltered.

    Examples
    --------
    >>> Path('foo.txt').write_text('Important stuff')
    ... with safe_write('foo.txt') as fp:
    ...     fp.write('Some additional text')
    ...     raise Exception('Catastrophy!')
    ... Path('foo.txt').read_text()
    'Important stuff'

    In the example above, the original content was restored upon exception.
    Catastrophy averted!

    Raises
    ------
    Exception
        The type and message of exceptions raised by this context manager are
        determined by the optional `exception_hook` function.
    """
    # write formatted entries
    # backup and restore on error!
    path = Path(filename).resolve()
    backup_needed = path.exists()
    if backup_needed:
        if backupfile is None:
            bid, backupfile = tempfile.mkstemp(prefix='backup.',
                                               suffix=f'.{path.name}')
        else:
            backupfile = Path(backupfile)

        # create the backup
        shutil.copy(str(path), backupfile)

    # write formatted entries
    with path.open(mode) as fp:
        try:
            yield fp
        except Exception as err:
            if backup_needed:
                fp.close()
                os.close(bid)
                shutil.copy(backupfile, filename)
            if exception_hook:
                raise exception_hook(err, filename) from err
            raise


@doc.splice(backed_up, 'summary', omit='Parameters[backupfile]',
            replace={'operation': 'write',
                     'read / ': ''})  # FIXME: replace not working here
def safe_write(filename, lines, mode='w', eol='\n', exception_hook=None):
    """
    {Parameters}
    lines : list
        Lines of content to write to file.
    """
    assert isinstance(eol, str)
    append = str.__add__ if eol else echo0
    
    with backed_up(filename, mode, exception_hook=exception_hook) as fp:
        # write lines
        try:
            for i, line in enumerate(lines):
                fp.write(append(line, eol))
        except Exception as err:
            if exception_hook:
                raise exception_hook(err, filename, line, i) from err
            raise


def write_replace(filename, replacements):
    if not replacements:
        # nothing to do
        return

    with backed_up(filename, 'r+') as fp:
        text = fp.read()
        fp.seek(0)
        fp.write(sub(text, replacements))
        fp.truncate()


def iocheck(instr, check, bork=0, convert=None):
    """
    Tests a input str for validity by calling the provided check function on it.
    Returns None if an error was found or raises ValueError if bork is set.
    Returns the original list if input is valid.
    """
    if not check(instr):
        msg = 'Invalid input!! %r \nPlease try again: ' % instr
        if bork == 1:
            raise ValueError(msg)
        elif bork == 0:
            print(msg)
            return
        elif bork == -1:
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
