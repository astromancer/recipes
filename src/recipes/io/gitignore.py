
import math
import glob
import fnmatch
from pathlib import Path


# ---------------------------------------------------------------------------- #
IGNORE_IMPLICIT = ('.git', )


# ---------------------------------------------------------------------------- #

def get_ignore_list(folder):

    if not (file := folder/'.gitignore').exists():
        raise FileNotFoundError(f"Could not find '{file!s}.'")

    return list(GitIgnore(file).search(folder))


class GitIgnore:
    """
    Class to read `.gitignore` patterns and filter source trees.
    """

    __slots__ = ('root', 'names', 'patterns')

    def __init__(self, path='.gitignore'):
        self.names = self.patterns = ()
        path = Path(path)
        self.root = path.parent

        if not path.exists():
            return

        # read .gitignore patterns
        lines = (line.strip(' /')
                 for line in path.read_text().splitlines()
                 if not line.startswith('#'))

        items = names, patterns = [], []
        for line in filter(None, lines):
            items[glob.has_magic(line)].append(line)

        self.names = (*IGNORE_IMPLICIT, *names)
        self.patterns = tuple(patterns)

    def match(self, filename):
        path = Path(filename).relative_to(self.root)
        filename = str(path)
        for pattern in self.patterns:
            if fnmatch.fnmatchcase(filename, pattern):
                return True

        return filename.endswith(self.names)

    def iter(self, folder=None, depth=any, _level=0):
        depth = math.inf if depth is any else depth
        folder = folder or self.root

        _level += 1
        if _level > depth:
            return

        for path in folder.iterdir():
            if self.match(path):
                continue

            if path.is_dir():
                yield from self.iter(path, depth, _level)
                continue

            yield path

    def match(self, filename):
        path = Path(filename)
        rpath = path.relative_to(self.root)
        filename = str(rpath)
        for pattern in self.patterns:
            if fnmatch.fnmatchcase(filename, pattern):
                return True

        return filename.endswith(self.names)

