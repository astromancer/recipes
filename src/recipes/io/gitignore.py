
# std
import math
import glob
import fnmatch
from pathlib import Path

# relative
from .. import op
from ..functionals import negate
from . import read_lines


# ---------------------------------------------------------------------------- #

def get_ignore_list(folder):

    if not (file := folder/'.gitignore').exists():
        raise FileNotFoundError(f"Could not find '{file!s}.'")

    return list(GitIgnore(file).search(folder))


# @cached.to_file(CACHE, typed={'filename': io.md5sum})
# def write_ignored():
    # io.write_lines(filename, map(str, to_ignore))


# if __name__ == '__main__':
#     write_ignores(CACHE / 'gitignored.txt')


# ---------------------------------------------------------------------------- #

class GitIgnore:
    """
    Class to read `.gitignore` patterns and filter source trees.
    """

    def __init__(self, path='.gitignore'):
        self.names = self.patterns = ()
        path = Path(path)
        if not path.exists():
            return

        # read .gitignore patterns
        lines = read_lines(path, strip='\n /', filtered=negate(op.startswith('#')))

        items = names, patterns = [], []
        for line in filter(None, lines):
            items[glob.has_magic(line)].append(line)

        self.names = tuple(names)
        self.patterns = tuple(patterns)

    def match(self, filename):
        filename = str(filename)
        for pattern in self.patterns:
            if fnmatch.fnmatchcase(filename, pattern):
                return True
        return filename.endswith(self.names)

    def search(self, folder, depth=math.inf, _level=0):
        _level += 1
        if _level > depth:
            return

        for path in folder.iterdir():
            if self.match(path):
                yield path
                continue

            if path.is_dir():
                yield from self.search(path, depth, _level)
