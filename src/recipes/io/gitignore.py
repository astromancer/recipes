
import math
import glob
import fnmatch
from pathlib import Path
from collections import abc


# ---------------------------------------------------------------------------- #
IGNORE_IMPLICIT = ('.git', )

# ---------------------------------------------------------------------------- #


def get_repo_files(folder):

    if not (file := Path(folder) / '.gitignore').exists():
        raise FileNotFoundError(f"Could not find '{file!s}.'")

    return list(GitIgnore(file).iterdir(folder))


def read(path):
    # read glob patterns from file
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'No such file: {path!s}.')

    return list(_read(path))


def _read(path):
    return filter(None, (line.strip(' ')
                         for line in path.read_text().splitlines()
                         if not line.startswith('#')))


class GlobPatternList:
    """
    Class to filter files matching any in a list of glob patterns.
    """

    __slots__ = ('root', 'names', 'patterns')

    @classmethod
    def from_file(cls, path):
        path = Path(path)
        return cls(path.parent, read(path))

    fromfile = from_file

    def __init__(self, root, patterns):
        self.root = Path(root)
        self.names = list(IGNORE_IMPLICIT)
        self.patterns = []
        self.add(patterns)

    def add(self, items):
        if isinstance(items, str):
            self._add(items)
        elif isinstance(items, abc.Iterable):
            list(map(self.add, items))
        else:
            raise TypeError(f'Invalid object type {type(items).__name__}: {items}.')
        
    def _add(self, pattern):
        items = (self.names, self.patterns)
        if pattern:
            items[glob.has_magic(pattern)].append(pattern.rstrip('/'))

    def match(self, filename):
        path = Path(filename).relative_to(self.root)
        filename = str(path)
        for pattern in self.patterns:
            if fnmatch.fnmatchcase(filename, pattern):
                return True

        return filename.endswith(tuple(self.names))

    def iterdir(self, folder=None, depth=any, _level=0):
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
        return super().__init__(path.parent, read(path))
