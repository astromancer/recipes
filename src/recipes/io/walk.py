
# std
import os
import glob
from enum import Enum
from pathlib import Path

# third-party
import more_itertools as mit
from loguru import logger

# relative
from . import globlist
from ..containers import ensure
from ..string.delimited import braces
from .brace_expressions import brace_expand_iter


# ---------------------------------------------------------------------------- #

class IgnoreFile(Enum):

    EMPTY = None
    SEARCH = 1

    @classmethod
    def _missing_(cls, value):
        return cls.EMPTY if ensure.is_null(value, ()) else None

    @classmethod
    def search(cls, path):

        parent_folders = path.parents
        if Path.cwd() in parent_folders and (_ignore := Path('.gitignore')).exists():
            return _ignore.resolve()

        for parent in parent_folders:
            if (_ignore := parent / '.gitignore').exists():
                return _ignore

        return None

    @classmethod
    def resolve(cls, ignore_file, path):

        # resolve path
        if isinstance(ignore_file, (str, Path)):
            ignore_file = Path(ignore_file).expanduser().absolute()
            if not ignore_file.exists():
                raise FileNotFoundError(
                    f"File or directory does not exist: '{path}'."
                )

            if ignore_file.parent not in path.parents:
                logger.warning(
                    'Path {} is not in the same folder tree as the ignore file: {}',
                    path, ignore_file
                )

            return ignore_file

        if ignore_file is cls.SEARCH:
            return cls.search(path)

        if cls(ignore_file) is cls.EMPTY:
            return None

        raise ValueError(f'Could not resolve ignore_file from: {ignore_file!r}.')


# ---------------------------------------------------------------------------- #

class FilePatternWalker:

    def __init__(self,  extensions=all, ignore_file=None, ignore_patterns=()):
        """
        Initialize a FilePatternWalker for iterating over files with pattern
        matching. Sets up file extension filters and ignore rules for walking
        file trees.

        Parameters
        ----------
        extensions : str or tuple of str, optional
            The filename extensions to include when walking directories.
            Defaults to :py:func:`all`, which is the sentinel to yield all files
            in a given folder. Thi values can also be a list of strings
            specifying extensions, or glob patterns, for matching filenames. For
            example, passing :python:`extensions=('py', 'txt')` is a the same as
            using the search pattern ``'*.{py,txt}'``.
        ignore_file : str or Path, optional
            Path to text file containing glob ignore patterns, eg:
            ``'.gitignore'``.
        ignore_patterns : tuple or str, optional
            Any explicit patterns to ignore when walking files.

        """
        # include_hidden : bool, default False
        # If ``True``, The ``“**”`` pattern will match hidden directories.
        # self.include_hidden = bool(include_hidden)

        # unpack brace expressions in ignore patterns
        ignore_patterns = ensure.tuple(ignore_patterns or (), coerce=str)
        ignore_patterns = mit.collapse(map(brace_expand_iter, ignore_patterns))
        self.ignore = globlist.load(ignore_file, list(ignore_patterns))

        # create glob pattern from list of file extensions
        if not extensions or extensions is all:
            # Note no dot here since we want filenames without extensions too
            self.extensions = '*'
        else:
            # comvert extension list to brace expansion pattern
            extensions = ensure.tuple(extensions, coerce=str)
            self.extensions = \
                f'.{{{",".join((ext.lstrip(".") for ext in extensions))}}}'

    def walk(self, path_or_pattern, recurse=True):
        """
        Generator that yields existing system files matching a given input
        pattern, optionally recursing down the folder tree. Input may be a file
        globbing pattern, a brace expansion pattern, or a pathlike.

        If a pattern of filename extensions is defined at :attr:`extensions`,
        only files matching that pattern will be yielded. Similarly, files
        matching any of the predefined ignore patters in :attr:`ignore` are
        skipped.

        Note that directories will not be returned if *recurse* is ``True``.

        Parameters
        ----------
        path_or_pattern : str or Path
            Path or pattern to unpack into an iterable of filenames. Input
            paths are converted to string before being processed as follows:

            - If the pattern in an existing file, it is yielded.
            - If the pattern in an existing folder, it is walked. Subfolders are
              also walked if *recurse* is ``True``.
            - If the string contains glob patterns, those will be adhered to.
              Note that recursive glob patterns may return the same file
              multiple times.
            - If the input string contains any brace expansion patterns, eg:
              ``'folder/file{1..5}.txt'`` or  ``'.git{,ignore}'`` those will be
              expanded.
            - Brace expressions may be combined with glob expressions to allow
              traversing multiple directory trees with a single call, eg:
              ``{a,b,c}/folder/**/*.py'``.

        recurse : bool, optional
            Whether to traverse subdirectories recursively.

        Yields
        ------
        pathlib.Path
            Path object for each file found.

        Raises
        ------
        FileNotFoundError
            If the provided path or pattern does not resolve to an existing file
            or directory.
        """
        path_or_pattern = str(path_or_pattern)

        # handle brace expansion first
        special = bool(braces.match(path_or_pattern, must_close=True))
        wildcard = glob.has_magic(path_or_pattern)  # handle glob patterns
        if special | wildcard:
            logger.opt(lazy=True).debug(
                'Special pattern detected: {!s}',
                lambda: _maybe_newline(path_or_pattern)
            )
            if special:
                itr = brace_expand_iter(path_or_pattern)
            else:
                itr = glob.iglob(path_or_pattern, recursive=recurse)

            for path in itr:
                # recurse
                # logger.trace('Recursing into: {!s}.', path)
                yield from self.walk(path, recurse)

            # break recursion
            return

        # Since the brace/glob patterns have been expanded recursively, we
        # should now have a file or folder
        if not (path := Path(path_or_pattern)).exists():
            raise FileNotFoundError(
                'The `path_or_pattern` parameter should be a path to an '
                f'existing file or folder. Recieved: {path_or_pattern!r}'
            )

        yield from self._walk(path, recurse)

    def _walk(self, path, recurse):

        logger.debug('Iterating over: {!s}. recurse = {}', path, recurse)

        if self.ignore.match(path):
            return

        # Return the input if it is an existing file. This breaks the recurrence.
        if path.is_file():
            yield path
            return

        if path.is_dir():
            # iterate all files with given extensions
            pattern = f'{path!s}/{"**/" * recurse}*{self.extensions}'
            logger.debug('Recursing on pattern: {}', pattern)

            yield from self.walk(pattern, recurse=recurse)
            return

        # Non-existing path
        raise ValueError(
            f"Could not any resolve files for the input pattern: '{path!s}'. "
            'Please supply a path to a valid existing directory, or '
            'alternitively a glob pattern, or bash brace expansion pattern.'
        )


# ---------------------------------------------------------------------------- #

def walk(folder, depth=1):
    """
    Walk the system path, but only up to the given depth.
    """
    # adapted from: http://stackoverflow.com/a/234329/1098683

    folder = folder.rstrip(os.path.sep)
    assert os.path.isdir(folder)

    n_sep = folder.count(os.path.sep)
    for root, dirs, files in os.walk(folder):
        yield root, dirs, files

        level = root.count(os.path.sep)
        if n_sep + depth <= level:
            del dirs[:]


# ---------------------------------------------------------------------------- #

def iter_files(path_or_pattern, extensions='*', recurse=False, ignore=()):
    """
    Generator that yields all files in a directory tree with given file
    extension(s), optionally recursing down the directory tree. Brace expansion
    syntax from bash is supported, allowing multiple directory trees to be
    traversed with a single statement.

    Parameters
    ----------
    path_or_pattern : str or Path
        Location of the root folder. Can also be a glob pattern of filenames to
        load eg: ``'/path/SHA_20200715.000[1-5].fits'``. Pattern can also
        contain brace expansion patterns eg:
        ``'/path/SHA\_202007{15..18}.000[1-5].fits'`` in which case all valid
        files and directories in the range will be traversed.
    extensions : str or tuple or list
        The filename extensions to consider. All filenames ending on any of
        these extensions are included. The same functionality as is provided by
        this parameter can be acheived by including the list of file extensions
        in the expansion pattern. eg: ``'/path/*.{png,jpg}'`` will get all png
        and jpg files from path directory.
    recurse : bool, default=True
        Whether or not to recurse down the directory tree. The same as using
        ``".../**/..."`` in the glob pattern.
    ignore : sequence
        List of filename glob patterns to ignore when traversing the tree.

    Examples
    --------
    >>> iter_files()

    Yields
    ------
    pathlib.Path
        System path pointing to the file.

    Raises
    ------
    ValueError
        If the given base path does not exist.
    """
    ignore = ensure.tuple(ignore or (), coerce=str)
    ignore = list(mit.collapse(map(brace_expand_iter, ignore)))

    yield from FilePatternWalker(extensions).walk(path_or_pattern, recurse)


def iter_package_files(file_or_folder, recurse=True, extensions='.py',
                       ignore_patterns=(), ignore_file=IgnoreFile.SEARCH):

    path = Path(file_or_folder).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File or directory does not exist: '{path}'.")

    ignore_file = IgnoreFile.resolve(ignore_file, path)
    walker = FilePatternWalker(extensions, ignore_file, ignore_patterns)
    yield from walker.walk(file_or_folder, recurse)


def _maybe_newline(string, width=40, indent=' ' * 2):
    return f'\n{indent}{string}' if len(string) > width else string
