
import math
import glob
import fnmatch
from pathlib import Path


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
        items = names, patterns = [], []
        for line in filter(None, patterns):
            items[glob.has_magic(line)].append(line)

        self.root = Path(root)
        self.names = (*IGNORE_IMPLICIT, *names)
        self.patterns = tuple(patterns)

    def match(self, filename):
        path = Path(filename).relative_to(self.root)
        filename = str(path)
        for pattern in self.patterns:
            if fnmatch.fnmatchcase(filename, pattern):
                return True

        return filename.endswith(self.names)

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
