
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
    # read glob patterns from file
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

    __slots__ = ('names', 'patterns')

    # @classmethod
    # def load(cls, filename=None, patterns=()):
    #     if filename:
    #         ignore = cls(filename)
    #         ignore.add(patterns)
    #     else:
    #         ignore = GlobPatternList(patterns)

    #     return ignore

    @classmethod
    def from_file(cls, path):
        path = Path(path)
        return cls(path.parent, read(path))

    fromfile = from_file

    def __init__(self, patterns):
        self.names = list(IGNORE_IMPLICIT)
        self.patterns = []
        self.add(patterns)

    def add(self, items):

        if isinstance(items, (str, Path)):
            self._add(str(items))

        elif isinstance(items, abc.Iterable):
            list(map(self.add, items))

        elif isinstance(items, GlobPatternList):
            self.names.extend(items.names)
            self.patterns.extend(items.patterns)

        else:
            raise TypeError(f'Invalid object type {type(items).__name__}: {items}.')

    def _add(self, pattern):
        items = (self.names, self.patterns)
        if pattern:
            # FIXME: trailing slash is signigficant. should only match
            # directories if present
            items[glob.has_magic(pattern)].append(pattern.rstrip('/'))

    def match(self, filename, root='/'):

        path = Path(filename).relative_to(root)
        filename = str(path)

        matcher = ftl.partial(fnmatch.fnmatchcase, filename)
        return any(map(matcher, self.patterns)) or filename.endswith(tuple(self.names))

    # def walk(self, folder, depth=any, extensions=all):

    #     if not (folder := Path(folder)).exists():
    #         raise NotADirectoryError(
    #             'The `folder` parameter should be a path to an existing system '
    #             f' folder. Recieved: {folder!r}'
    #         )

    #     depth = DEPTH_LIMIT if depth is any else depth
    #     extensions = resolve_extensions(extensions)
    #     yield from self._walk(folder, depth, extensions)

    # def _walk(self, folder, depth, extensions, _level=0):

    #     _level += 1
    #     if _level > depth:
    #         return

    #     for path in folder.iterdir():
    #         if extensions and path.suffix not in extensions:
    #             continue

    #         if self.match(path, folder):
    #             continue

    #         if path.is_dir():
    #             yield from self._walk(path, depth, _level)
    #             continue

    #         yield path

    # # alias
    # iter = iterdir = walk


class GitIgnore(GlobPatternList):
    """
    Class to read `.gitignore` files and filter source trees.
    """

    __slots__ = ('root', )

    def __init__(self, filename='.gitignore'):
        path = Path(filename)
        super().__init__(read(path))
        self.root = path.parent

    def match(self, filename, root=None):
        return super().match(filename, root or self.root)

    # def walk(self, folder, depth=any, extensions=all):
    #     return super().walk(folder or self.root, depth, extensions)

    # # alias
    # iter = iterdir = walk
