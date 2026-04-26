
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

    __slots__ = ('names', 'folders',  'subpaths', 'abspaths', 'patterns')

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

    def __init__(self, patterns):
        self.names = []
        self.folders = []
        self.subpaths = []
        self.abspaths = []
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
        items : str or Path or iterable of str or GlobPatternList
            Glob pattern(s) to add.

        Raises
        ------
        TypeError
            If input is not a string, a Path, an iterable of strings, or a
            GlobPatternList.
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
        if not pattern:
            return

        if glob.has_magic(pattern):
            return self.patterns.append(pattern)

        if pattern.startswith('/'):
            return self.abspaths.append(pattern)

        if pattern.endswith('/'):
            #  trailing slash is signigficant. should only match directories
            # if present
            return self.folders.append(pattern.rstrip('/'))

        if '/' in pattern:
            return self.subpaths.append(pattern)

        self.names.append(pattern)

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
        return (
            (filename := str(filename)) in self.abspaths
            or (path := Path(filename)).name in self.names
            or path.is_dir() and path.name in self.folders
            or filename.endswith(tuple(self.subpaths))
            or any(map(ftl.partial(self._match, filename), self.patterns))
        )

    def _match(self, filename, pattern):
        # handle negated patterns
        if negate := pattern.startswith('!'):
            pattern = pattern.replace('!', '', 1)

        matched = fnmatch.fnmatchcase(filename, pattern)
        return (not matched) if negate else matched


class GitIgnore(GlobPatternList):
    """
    Class to read `.gitignore` files and filter source trees.
    """

    def __init__(self, filename='.gitignore'):
        path = Path(filename)
        super().__init__(read(path))
        self.names.extend(IGNORE_IMPLICIT)
