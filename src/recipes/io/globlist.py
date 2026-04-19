
import glob
import fnmatch
import functools as ftl
from pathlib import Path
from collections import abc

# ---------------------------------------------------------------------------- #
IGNORE_IMPLICIT = ('.git', )

# ---------------------------------------------------------------------------- #


def get_repo_files(folder):

    if not (file := Path(folder) / '.gitignore').exists():
        raise FileNotFoundError(f"Could not find '{file!s}.'")

    return list(GitIgnore(file).walk(folder))


def read(path):
    """
    Read glob patterns from a file.

    Parameters
    ----------
    path : str or Path
        Path to the file containing glob patterns.

    Returns
    -------
    list of str
        A list of glob patterns that were read from the file.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'No such file: {path!s}.')

    return list(_read(path))


def _read(path):
    return filter(None, (line.strip(' ')
                         for line in path.read_text().splitlines()
                         if not line.startswith('#')))


def load(filename=None, patterns=()):

    if filename:
        ignore = GitIgnore(filename)
        ignore.add(patterns)
    else:
        ignore = GlobPatternList(patterns)

    return ignore


def resolve_extensions(extensions):

    if extensions in {all, None}:
        return ()

    if isinstance(extensions, str):
        extensions = (extensions, )

    return tuple(f'.{e.lstrip(".")}' for e in extensions)


class GlobPatternList:
    """
    Class to filter files matching any in a list of glob patterns.
    """

    __slots__ = ('root', 'names', 'patterns')

    @classmethod
    def from_file(cls, path):
        """
        Create a GlobPatternList from a file containing glob patterns.

        Parameters
        ----------
        path : str or Path
            Path to the file containing glob patterns.

        Returns
        -------
        GlobPatternList
            An instance of GlobPatternList initialized with patterns
            from the file.
        """
        path = Path(path)
        return cls(path.parent, read(path))

    # alias
    fromfile = from_file

    def __init__(self, root, patterns):
        self.root = Path(root)
        self.names = list(IGNORE_IMPLICIT)
        self.patterns = []
        self.add(patterns)

    def pprint(self):
        print(''.join(
            ''.join((attr, ' =\n',
                     '    ', '\n    '.join(getattr(self, attr)), '\n'))
            for attr in self.__slots__
        ))

    def add(self, items):
        """
        Add glob patterns to the list.

        Parameters
        ----------
        items : str or iterable of str
            Glob pattern(s) to add.

        Raises
        ------
        TypeError
            If input is not a string or an iterable of strings.
        """
        if isinstance(items, (str, Path)):
            self._add(str(items))

        elif isinstance(items, abc.Iterable):
            list(map(self.add, items))

        elif isinstance(items, GlobPatternList):
            for attr in self.__slots__:
                getattr(self, attr).extend(getattr(items, attr))

        else:
            raise TypeError(
                f'Invalid object type {type(items).__name__}: {items}.'
            )

    def _add(self, pattern):
        if pattern:
            items = (self.names, self.patterns)
            items[glob.has_magic(pattern)].append(pattern.rstrip('/'))


    def match(self, filename):
        """
        Check if a filename matches any of the glob patterns or names.

        Parameters
        ----------
        filename : str or Path
            The filename to check.

        Returns
        -------
        bool
            True if the filename matches any pattern or name, False otherwise.
        """

        path = Path(filename).relative_to(self.root)
        filename = str(path)
        return next(
            (
                True
                for pattern in self.patterns
                if fnmatch.fnmatchcase(filename, pattern)
            ),
            filename.endswith(tuple(self.names)),
        )

    def iterdir(self, folder=None, depth=any, _level=0):
        """
        Iterate over files and directories, filtering by glob patterns.

        Parameters
        ----------
        folder : str or Path, optional
            The folder to iterate over. Defaults to the root path.
        depth : int or any, optional
            The maximum recursion depth. Defaults to infinite recursion.

        Yields
        ------
        Path
            Paths of files and directories that do not match any of the
            glob patterns.
        """

        depth = math.inf if depth is any else depth
        folder = folder or self.root

        _level += 1
        if _level > depth:
            return

        for path in folder.iterdir():
            if self.match(path):
                continue

            if path.is_dir():
                yield from self.iterdir(path, depth, _level)
                continue

            yield path

    # alias
    iter = iterdir


class GitIgnore(GlobPatternList):
    """
    Class to read `.gitignore` files and filter source trees.
    """

    def __init__(self, filename='.gitignore'):
        path = Path(filename)
        patterns = read(path) if path.exists() else []
        super().__init__(path.parent, patterns)
