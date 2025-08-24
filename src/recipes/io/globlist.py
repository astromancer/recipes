
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

    __slots__ = ('names', 'folders',  'subpaths', 'abspaths', 'patterns')

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

    # __slots__ = ('root', )

    def __init__(self, filename='.gitignore'):
        path = Path(filename)
        super().__init__(read(path))
        self.names.extend(IGNORE_IMPLICIT)
        # self.root = path.parent

    def match(self, filename, root=None):
        return super().match(filename)

    # def walk(self, folder, depth=any, extensions=all):
    #     return super().walk(folder or self.root, depth, extensions)

    # # alias
    # iter = iterdir = walk
