
# std libs
import os
from recipes.string import replace_prefix
from recipes.io import open_any
import functools as ftl
from recipes.io import iter_lines
from recipes.string import truncate
from recipes.dicts import DefaultDict
from recipes.io import read_lines
from ..regex import split_iter
import io
import ast
import sys
import math
import inspect
import warnings as wrn
import itertools as itt
from pathlib import Path
from functools import partial
from collections import defaultdict

# third-party libs
import anytree
from stdlib_list import stdlib_list

# relative libs
from ..io import write_lines, safe_write, count_lines
from ..functionals import always, echo0 as echo


# FIXME: unscoped imports do not get added to top!!!
# FIXME: too many blank lines after module docstring
# FIXME: from recipes.oo import SelfAware, meta # where meta is unused!


# TODO: convert to relative imports
# TODO: split_modules
# TODO: style preference: "import uncertainties.unumpy as unp" over
#                         "from uncertainties import unumpy as unp"
# TODO: keep multiline imports as multiline
# TODO: local import that are already in global namespace

from recipes.logging import logging, get_module_logger

# module level logger
logger = get_module_logger()
logging.basicConfig()
logger.setLevel(logging.INFO)

# list of builtin modules
easterEggs = ['this', 'antigravity']
unlisted = ['keyword']  # auto-generated module for builtin keywords
builtin_module_names = stdlib_list(sys.version[:3]) + easterEggs + unlisted

# object that finds system location of module from name
# pathFinder = PathFinder()

# internal sorting codes
MODULE_GROUP_NAMES = ['std', 'third-party', 'local', 'relative']
GROUP_NAME_SUFFIX = 'libs'

# list of local module names
LOCAL_MODULES_DB = Path.home() / '.config/recipes/local_libs.txt'
LOCAL_MODULES = LOCAL_MODULES_DB.read_text().splitlines()

STYLES = ('alphabetic', 'aesthetic')


F_NAMEMAX = os.statvfs('.').f_namemax


# function that always returns 0
zero = always(0)


def is_builtin(name):  # name.split('.')[0]
    return name in builtin_module_names


def is_local(name):
    return name in LOCAL_MODULES


# def is_3rd_party(name):
# TODO maybe check if available through pip ???
#     # check if module lives in `dist-packages` - these are likely 3rd party
#     spec = pathFinder.find_spec(name)
#     if spec is None:
#         # the list below are known 3rd party modules for which the pathFinder
#         # returns None
#         return False
#
#     return ('dist-packages' in spec.origin) or ('site-packages' in spec.origin)


def is_import_node(st):
    return isinstance(st, (ast.ImportFrom, ast.Import))


def get_module_typecode(module_name):
    if is_import_node(module_name):
        module_name = get_modules_list(module_name, depth=0)

    if is_builtin(module_name):
        return 0
    if is_local(module_name):
        return 2
    if module_name == '.':
        return 3
    return 1
    # if is_3rd_party(module_name):
    #     return 1


def get_module_kind(module_name):
    return MODULE_GROUP_NAMES[get_module_typecode(module_name)]


def get_modules_list(node, split=True, depth=None):
    # get the module name from an Import or ImportFrom node. Assumes one
    # module per statement
    if not split:
        depth = None
    if depth:
        split = True

    idx = 0 if depth == 0 else slice(depth)
    if isinstance(node, ast.ImportFrom):
        if node.level:
            # this is a module relative import
            names = ['.'] * node.level
            if node.module:
                names += node.module.split('.')
            if not split:
                return ''.join(names[idx])
            return names[idx]

            # names = (('.' * node.level) + (node.module or ''))
            # names = names.split('.')[idx]
            # return (''.join, list)[split](names[idx])

        names = node.module
    elif isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
        if len(names) == 1:
            names = names[0]
        else:
            TypeError(
                f'Encountered `import {", ".join(names)}`.' +
                'Please split single line, multi-module import '
                'statements first.  This can be done by using '
                '`ImportCapture(split=True).visit(ast.parse(source_code))`'
            )
    else:
        raise TypeError('Invalid Node type %r' % node)

    if split:
        return names.split('.')[idx]
    return names


def _sort(node):
    return getattr(node, 'order', 0)


def sort_nodes(nodes):
    return sorted(nodes, key=_sort)


def grouper(statements, func):
    groups = defaultdict(list)
    for stm in statements:
        groups[func(stm)].append(stm)
    return groups.items()


def get_style_groups(statements):
    # moduleNameCount = defaultdict(int)
    moduleIsFrom = defaultdict(list)

    # count how many times any given module is used in import
    # statements, and check whether there are ImportFrom style
    # imports for this module
    for node in statements:
        name = get_modules_list(node)[0]
        # moduleNameCount[name] += 1
        moduleIsFrom[name].append(isinstance(node, ast.ImportFrom))

    # some logic on the ImportFrom statements to help with sorting.
    # Make groups for modules having
    #   0: only `import x` style;
    #   1: mixed styles: eg: `import x`; `from x.y import a`
    #   2: only  `from x import y` style
    return {m: any(b) + all(b)
            for m, b in moduleIsFrom.items()}

# def print_imports_tree2(tree, ws=50):
#     print(RenderTree(tree).by_attr('stm'))

# def depends_on(filename, up_to_line=None):  # TODO
#     code = get_block(filename, up_to_line)
#     tree = ast.parse(code)
#     visitor = ModuleExtractor()
#     visitor.visit(tree)
#     return visitor.modules


class NodeFilter(ast.NodeTransformer):
    def __init__(self, remove=(), keep=(ast.AST,)):
        self.keep = tuple(set(keep))
        self.remove = tuple(set(remove))

    def visit(self, node):
        if isinstance(node, self.keep) and not isinstance(node, self.remove):
            return super().visit(node)


class Parentage(ast.NodeTransformer):
    # for consistency, module parent is None
    parent = None

    def visit(self, node):
        node.parent = self.parent
        self.parent = node
        node = super().visit(node)
        if isinstance(node, ast.AST):
            self.parent = node.parent
        return node


class ImportCapture(Parentage):
    def __init__(self, up_to_line=math.inf):
        self.parent = None
        self.up_to_line = up_to_line or math.inf  # internal line nrs are 1 base
        self.line_nrs = []
        self.used_names = defaultdict(set)
        self.imported_names = defaultdict(set)

    def _should_capture(self, node):
        return (node.lineno <= self.up_to_line) and (node.col_offset == 0)

    # def visit_Module(self, node):
    #     # first call to `generic_visit` will build the tree as well as capture
    #     # all the  imported names and used names
    #     return self.generic_visit(node)

    def _visit_any_import(self, node):
        node = self.generic_visit(node)
        if not self._should_capture(node):
            return node

        # capture line numbers
        self.line_nrs.append(node.lineno - 1)
        return node

    def visit_Import(self, node):
        return self._visit_any_import(node)

    def visit_ImportFrom(self, node):
        return self._visit_any_import(node)

    def visit_alias(self, node):
        name = node.asname or node.name
        if name != '*':
            self.imported_names[node.parent.parent].add(name)
        return node

    def visit_Name(self, node):
        self.used_names[node.parent].add(node.id)
        return node

    def visit_Attribute(self, node):
        node = self.generic_visit(node)
        if isinstance(node.value, ast.Name):
            self.used_names[node.parent].add(f'{node.value.id}.{node.attr}')
        return node


class ImportFilter(ast.NodeTransformer):
    def __init__(self, names=()):
        self.remove = set(names)

    def visit_Module(self, node):
        if not self.remove:
            return node

        return self.generic_visit(node)

    def _visit_any_import(self, node):
        node = self.generic_visit(node)
        if node.names:
            return node
        # if all aliases were removed, import node is filtered from tree

    def visit_Import(self, node):
        return self._visit_any_import(node)

    def visit_ImportFrom(self, node):
        return self._visit_any_import(node)

    def visit_alias(self, node):
        node = self.generic_visit(node)
        name = node.asname or node.name
        if name in self.remove:
            logger.debug('Removing unused import: %s', name)
            return
        return node

    #     # if self.up_to_line < math.inf:
    #     #     wrn.warn(
    #     #         'With `up_to_line` given and finite, we cannot determine the '
    #     #         'complete list of used names in module, and therefore cannot '
    #     #         'filter the unused names reliably. Please use '
    #     #         '`filter_unused=False` for partial file import refactoring.'
    #     #     )

    #     # if not self.used_names:
    #     #     wrn.warn(
    #     #         'ImportFilter encountered module containing only import '
    #     #         'statements. This will remove all import statements from the '
    #     #         'module, which is probably not what you intended. Please use '
    #     #         '`filter_unused=False` if you only wish to sort existing import'
    #     #         ' statements.'
    #     #     )

        # next filter stuff we don't want


class ImportMerger(Parentage):
    # combine separate statements that import from the same module
    # >>> from x import y
    # >>> from x import z
    # becomes
    # >>> from x import y, z

    def __init__(self, level=1):  #
        # [scope][module]{node}
        self.aliases = defaultdict(dict)

    def visit_ImportFrom(self, node):
        self.generic_visit(node)

        scoped = self.aliases[node.parent]
        module_name = node.module or '.' * node.level
        new_node = scoped.setdefault(module_name, node)
        if node is new_node:
            return node

        scoped[module_name].names.extend(node.names)


class ImportSplitter(ImportMerger):
    def __init__(self, level=0):
        super().__init__()
        self.level = level if isinstance(level, (list, tuple)) else [int(level)]

    def visit_Import(self, node):
        node = self.generic_visit(node)
        if (0 in self.level) and (len(node.names) > 1):
            # split 1 line multi-module statements like:
            # >>> import os, re, this
            # into many lines
            return [ast.Import([ast.alias(alias.name, alias.asname)])
                    for alias in node.names]

        return node

    def visit_ImportFrom(self, node):
        node = self.generic_visit(node)
        if (1 in self.level) and (len(node.names) > 1):
            # split 1 line multi-module statements like:
            # >>> from xx import yy as uu, zz as vv
            # into many lines
            # from xx import yy as uu
            # from xx import zz as vv
            node = super().visit_ImportFrom(node)
            # split
            if len(node.names) > 1:
                return [ast.ImportFrom(node.module,
                                       [ast.alias(alias.name, alias.asname)],
                                       node.level)
                        for alias in node.names]
        return node


class ImportRelativizer(ast.NodeTransformer):
    def __init__(self, module_name):
        self.module_name = str(module_name)

    def visit_ImportFrom(self, node):
        node = self.generic_visit(node)
        if node.module and not node.level:
            node.module = replace_prefix(
                node.module, self.module_name, ('.', '')['.' in node.module]
            )
        return node


class OldImportRefactory(ImportCapture):
    # TODO: scope aware capture

    def __init__(self, up_to_line=math.inf, split=True,
                 filter_unused=False, merge=True, rename=()):
        super().__init__(up_to_line)

        if filter_unused and (self.up_to_line < math.inf):
            raise ValueError(
                'With `up_to_line` given and finite, we cannot determine the '
                'complete list of used names in module, and therefore cannot '
                'filter the unused names reliably. Please use '
                '`filter_unused=False` for partial file import refactoring.'
            )

        self.split = bool(split)
        self.filter_unused = filter_unused
        self.merge = bool(merge)
        self.rename = dict(rename)
        #
        self.used_names = set()
        self.imported_names = []
        self._current_names = []

    def visit_Module(self, node):

        # first call to `generic_visit` will build the tree as well as capture
        # all the  imported names and used names
        module = self.generic_visit(node)

        if self.filter_unused is None:
            self.filter_unused = (self.up_to_line == math.inf
                                  and bool(self.used_names))
        if self.filter_unused and not self.used_names:
            wrn.warn(
                '`filter_unused` requested but no code statements (besides '
                'imports) detected. This will remove all import statements from'
                ' the source, which is probably not what you intended. Please '
                'use `filter_unused=False` if you only wish to sort existing '
                'import statements.'
            )

        if self.merge:
            new_body = merge_by_module(new_body)

        return ast.Module(new_body)

    def visit_Import(self, node):
        node = self.generic_visit(node)
        if not self._should_capture(node):
            return node

        # capture line numbers
        self.line_nrs.append(node.lineno - 1)

        # split 1 line multi-module statements like:
        # >>> import os, re, this
        # into many lines
        if self.split and len(node.names) > 1:
            new_nodes = [ast.Import([ast.alias(alias.name, alias.asname)])
                         for alias in node.names]

            for _ in self._current_names:
                self.imported_names.append([_])
        else:
            self.imported_names.append(self._current_names)  # extend?
            new_nodes = node

        self._current_names = []
        return new_nodes

    def visit_ImportFrom(self, node):
        node = self.generic_visit(node)
        if not self._should_capture(node):
            return node

        # capture line numbers and imported names
        self.line_nrs.append(node.lineno - 1)
        self.imported_names.append(self._current_names)
        self._current_names = []

        # rename
        if self.rename:
            level = 1
            return ast.ImportFrom(self.rename.get(node.module, node.module),
                                  node.names, level)

        return node


def rewrite(node, width=80):
    """write an import node as str"""
    s = ''
    if isinstance(node, ast.ImportFrom):
        # for module relative imports, `node.module` holds the sub-module
        s = f'from {"." * node.level}{node.module or ""} '

    # write the aliases
    s += 'import '
    aliases = [
        f'{alias.name}{f" as {alias.asname}" if alias.asname else ""}, '
        for alias in node.names
    ]
    aliases[-1] = aliases[-1].rstrip(', ')

    # check length
    mark, *splitx = itt.accumulate(map(len, aliases), initial=len(s))

    if splitx[-1] <= width:
        return ''.join((s, *aliases))

    # split lines
    # wrap imported names in a tuple
    s += '('
    mark = len(s)
    for i, l in enumerate(splitx):
        if l > width:
            # go to next line & indent to tuple mark
            s = f'{s.strip()}\n{"":<{mark}}'
        s += aliases[i]
    s += ')'
    return s


def merge_by_module(stm):
    # assumes sorted already

    stm = sorted(stm, key=partial(get_modules_list, split=False))

    r = []
    prev = None
    for i, st in enumerate(stm):
        if (i and
                    set(map(type, (st, prev))) == {ast.ImportFrom} and
                    st.module == prev.module and
                    st.level == prev.level
                ):

            names = {_.name for _ in prev.names}
            for alias in st.names:
                if alias.name not in names:
                    prev.names.append(alias)
                continue

        r.append(st)
        prev = st

    return r


# alias
merge_modules = merge_by_module


def gen_module_names(nodes):
    for node in nodes:
        if isinstance(node, ast.ImportFrom):
            if node.level:
                return '.'
            yield node.module.split('.')[0]

        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split('.')[0]


# def get_modules(node):
#     # get the module and submodule names from an Import or ImportFrom node.
#     # Assumes one
#     # module per statement
#     if isinstance(node, ast.ImportFrom):
#         if node.level:
#             return '.'
#         return node.module.split('.')[0]
#
#     if isinstance(node, ast.Import):
#         names = [alias.name for alias in node.names]
#         if len(names) == 1:
#             return names[0].split('.')[0]
#         else:
#             TypeError('Split single line multi-module import statements first.')
#
#     raise TypeError('Invalid Node type %r' % node)


class Node(anytree.Node):  # ImportNode
    def pprint(self, ws=50):
        """
        Print a representation of the tree along with the statements at each leaf

        Parameters
        ----------
        tree

        Returns
        -------

        """
        for pre, _, node in anytree.RenderTree(self, childiter=sort_nodes):
            # lvl = len(pre) // 4
            # stm = str(getattr(node, 'order', '')) + ' ' + getattr(node, 'stm', '')
            stm = getattr(node, 'stm', '')
            stm = stm.replace('\n',
                              f'\n{pre[: -4]}{"": <{len(str(node.name)) + 4}}')
            pre = f'{pre}{node.name}'
            w = ws - len(pre)
            print(f'{pre}{stm: >{w + len(stm)}s}')

    def gen_lines(self, headers=True, suffix=GROUP_NAME_SUFFIX):
        for pre, _, node in anytree.RenderTree(self, childiter=sort_nodes):
            lvl = len(pre) // 4
            if lvl == 1 and headers:
                # commented header for import group
                yield f'\n# {node.name} {suffix}'

            if hasattr(node, 'stm'):
                yield node.stm
                # separate groups by newline

    def make_branch(self, statements, funcs, sorts, lvl=0):
        func = funcs[lvl] if lvl < len(funcs) else None
        sorter = sorts[lvl] if lvl < len(sorts) else zero
        for child, _, grp in self._make_children(statements, func, sorter, lvl):
            # print(lvl, child, _, grp)
            child.make_branch(grp, funcs, sorts, lvl + 1)

    def _make_children(self, statements, func, sort, lvl):
        statements = first, *_ = list(statements)

        if func is None and sort is zero:
            # Deepest level. Leaf nodes get attributes here.
            # print('PING', lvl, rewrite(statements[0]))
            self.stm = rewrite(first)
            self.order = min(len(self.stm), 80)

            # order groups by maximal statement length
            if lvl >= 3:
                self.order = min(len(self.stm), 80)
                parent = self.parent
                for _ in range(3, lvl):
                    parent.order = max(self.order, parent.order)
                    parent = parent.parent

            return

        for gid, stm in grouper(statements, func):
            child = Node(gid, parent=self, order=sort(gid))
            yield child, gid, stm


class GroupingHelper:
    # Helper class for creating the lower branches of the tree (grouping
    # submodules)
    # basically a hack to create functions that return empty string if the key
    # is abscent
    def __init__(self, statements):
        # names = map(get_modules_list, statements)

        self.subs = [
            defaultdict(str, {s: su for s, su in zip(statements, sub) if su})
            for sub in itt.zip_longest(*map(get_modules_list, statements))
        ]
        # dict(zip(statements, sub))
        self.max_depth = len(self.subs)

    def __iter__(self):
        for i in range(self.max_depth):
            yield self.subs[i].__getitem__


# convenience functions

def refactor(filename,
             sort='aesthetic',
             filter_unused=None,
             split=0,
             merge=1,
             relativize=True,
             #  unscope=False,
             headers=None,
             report=False):

    # up_to_line=math.inf,
    # , keep_multiline=True,

    # return ImportRefactory(filename).refactor(
    #     sort, filter_unused, split, merge, relativize,  # unscope,
    # ).write(headers, report)

    refactory = ImportRefactory(filename)
    tree = refactory.refactor(sort, filter_unused, split,
                              merge, relativize)  # unscope,
    return refactory.write(tree, headers=headers, report=report)


# aliases
tidy = refactor


def get_stream(file_or_source):
    if isinstance(file_or_source, io.IOBase):
        return file_or_source

    if isinstance(file_or_source, str):
        if len(file_or_source) < F_NAMEMAX and Path(file_or_source).exists():
            return file_or_source

        # assume string is raw source code
        return io.StringIO(file_or_source)

    if isinstance(file_or_source, Path):
        if file_or_source.exists():
            return file_or_source

        raise FileNotFoundError(f'{truncate(file_or_source, 100)}')

    raise TypeError(
        f'Cannot interpret {type(file_or_source)} as file-like object.'
    )


class ImportRefactory:
    """
    Tidy up import statements that might lie scattered throughout hastily
    written source code. Sort them, filter unused, group them, re-write them in
    the document header or write to a new file or just print the prettified code
    to stdout.


    Parameters
    ----------
    filename: str or Path
        input filename
    up_to_line: int
        line number for last line in input file that will be processed
    """

    def __init__(self, file_or_source):

        with open_any(get_stream(file_or_source)) as file:
            self.source = file.read()

        self.filename = None
        if isinstance(file, io.TextIOWrapper):
            self.filename = file.buffer.name

        self.captured = ImportCapture()
        self.module = self.captured.visit(ast.parse(self.source))

    # def parse(self, stream):
    #     with open_any(stream) as file:
    #         return ImportCapture().visit(ast.parse(file.read()))

    # @ftl.cached_property
    # def lines(self):
    #     # line list. might be slow for excessively large codebase.
    #     return list(self.get_lines())

    # def get_lines(self):
    #     # NOTE: intentionally reading all the lines in the file. This is because
    #     # the ast might not parse if we cut the source code at some arbitrary
    #     # line.

    #     yield from iter_lines(self.filename)

    # def resolve_line_limit(self, n):
    #     n = n or math.inf
    #     if n == math.inf:
    #         return n

    #     n = int(n)
    #     if n < 0:
    #         # negative numbers are wrapped
    #         n += len(self.lines)
    #     return n

    def filter_unused(self, module=None):
        module = module or self.module
        imported_names = self.captured.imported_names[module]
        used_names = set().union(*self.captured.used_names.values())
        # used_names = self.captured.used_names[module]
        unused = set.difference(imported_names, used_names)

        if imported_names and not self.captured.used_names:
            wrn.warn(
                '`filter_unused` requested but no code statements (besides '
                'imports) detected. This will remove all import statements from'
                ' the source, which is probably not what you intended. Please '
                'use `filter_unused=False` if you only wish to sort existing '
                'import statements.'
            )

        return ImportFilter(unused).visit(module)

    # alias
    filter = filter_unused

    def merge(self, module=None, level=1):
        module = module or self.module
        return ImportMerger(level).visit(module)

    def split(self, module=None, level=0):
        module = module or self.module
        return ImportSplitter(level).visit(module)

    def relativize(self, module=None):
        module = module or self.module
        if not self.filename:
            return module

        # get the module name so we can replace
        # >>> from package.module import x
        # with
        # >>> from .module import x
        module_name = inspect.getmodulename(self.filename)
        return ImportRelativizer(module_name).visit(module)

    def sort(self, module=None, how='aesthetic'):
        module = module or self.module
        imports_only = NodeFilter(
            keep=(ast.Module, ast.Import, ast.ImportFrom, ast.alias)
        ).visit(module)

        return make_tree(imports_only.body, how)

    def refactor(self,
                 sort='aesthetic',
                 filter_unused=None,
                 split=0,
                 merge=1,
                 relativize=True):
        #  unscope=False):
        # keep_multiline=True,
        """

        sort: str, {'aesthetic', 'alphabetically'}
            The sorting rules are as follow: 
            # TODO
        unscope: bool
            Whether or not to move the import statements that are in a local scope
        headers: bool or None
            whether to print comment labels eg 'third-party libs' above different
            import groups.  If None (the default) this will only be done if there
            are imports from multiple groups.

        """

        module = self.module

        # if unscope:
        #     module = self.unscope(module)

        # filter_unused = (self.up_to_line == math.inf and bool(used_names))
        filter_unused = filter_unused or bool(self.captured.used_names)
        if filter_unused:
            module = self.filter(module)

        if split is not None:
            module = self.split(module, split)

        if merge is not None:
            module = self.merge(module, merge)

        if relativize:
            module = self.relativize(module)

        # if sort is not None:
        return self.sort(module, sort)

        # return module

    def unscope(self):
        return 'TODO'

    # def sort_imports(self,
    #                  how='aesthetic',
    #                  up_to_line=math.inf,
    #                  filter_unused=None,
    #                  prefer_relative=True,
    #                  unscope=False,
    #                  headers=None,
    #                  write_to=None,
    #                  dry_run=False,
    #                  report=False):

    #     # parse
    #     root, captured = self.get_import_tree(
    #         how, up_to_line, filter_unused, unscope, rename
    #     )

    def write(self, root, filename=None, headers=True, report=False):
        # module=None,
        """
        filename: str or Path
            output filename
        dry_run: bool
            if True, don't edit any files, instead return the re-shuffled source
            as a string.

        Returns
        -------
        sourceCode: str
            Reformatted source code as a str.
        """

        # at this point the import statements should be grouped and sorted
        # correctly in new tree
        if report:
            root.pprint()

        # module = module or self.module
        # overwrite input file if `filename` not given
        filename = filename or self.filename

        if len(root.children) == 0:
            # no imports - nothing to do
            if filename:
                return self
            return self.source

        # line generator
        lines = self._iter_rewrite(root, headers)

        # return the string if dry_run or reading from text stream
        if filename:
            safe_write(filename, lines)
            return self
        return '\n'.join(lines)

    def _iter_rewrite(self, root, headers=None):
        # keep_multiline=True
        # line generator

        # create new source code with import statements re-shuffled
        # group headings
        if headers is None:
            headers = (len(root.children) > 1)

        # line list. might be slow for large codebase
        lines = self.source.splitlines()

        # get line numbers for removal
        cutLines, _ = excision_flagger(lines, self.captured.line_nrs)
        first = cutLines[0]

        # write the document header
        yield from lines[:first]

        # write the ordered import statements (render the tree!)
        yield from root.gen_lines(headers)

        # finally rebuild the remaining source code, omitting the previously
        # extracted import lines
        n = 0  # number of successive newlines
        for i, line in enumerate(lines[first + 1:], first + 1):
            if i in cutLines:
                continue

            if line:
                n = 0
            else:
                n += 1

            # only yield empty lines if they are preceded by fewer than 2 newlines
            if n <= 2:
                yield line


def make_tree(statements, sort='aesthetic'):
    """
    Create a tree of import statements from a list of ast nodes. This divides
    the import statements into groups and assigns a positional `order` attribute
    to each to aid further sorting.

    Parameters
    ----------
    statements : list of ast.Node
        Import statements as `ast.Node` objects.
    aesthetic : bool, optional
        Whether to sort aesthetically, by default True. Mutually exclusive with
        `alphabetic` parameter.
    alphabetic : bool, optional
        Whether to sort statements alphabetically, by default False. Mutually
        exclusive with `alphabetic` parameter.

    Returns
    -------
    anytree.Node
        The root node of the new tree.
    """

    # collect the import statements
    root = Node('body')

    # no import statements ?
    if len(statements) == 0:
        return root

    sort = sort.lower()
    assert sort in STYLES
    if sort.startswith('aes'):
        # hierarchical group sorting for aesthetic
        importStyleGroups = get_style_groups(statements)

        def lvl1(stm):
            return importStyleGroups[get_modules_list(stm, depth=0)]

        # decision functions
        groupers = [get_module_kind, lvl1, *GroupingHelper(statements)]
        sorters = [MODULE_GROUP_NAMES.index, echo]

    else:
        raise NotImplementedError(sort)

    # make tree
    root.make_branch(statements, groupers, sorters)
    return root


def excision_flagger(lines, line_nrs):
    # We have to be careful with multi-line imports since ast has no special
    # handling for these ito giving statement line end numbers. Lines ending on
    # the line continuation character '\', and lines containing multi-line
    # tuples are handled below
    cutLines = []
    is_multiline = []
    for ln in line_nrs:
        # ln = s.lineno - 1
        line = lines[ln]
        cutLines.append(ln)

        # line continuation
        flag = False
        while line.endswith('\\'):
            ln += 1
            line = lines[ln]
            cutLines.append(ln)
            flag = True

        # multi-line tuple
        if '(' in line:
            while ')' not in line:
                ln += 1
                line = lines[ln]
                cutLines.append(ln)
                flag = True

        if flag:
            is_multiline.append(ln)

    # search through the document header for the import group headers so we
    # don't duplicate them
    search_depth = min(100, max(cutLines))
    # FIXME: ValueError: max() arg is an empty sequence
    for ln in (set(range(search_depth)) - set(cutLines)):
        line = lines[ln]
        if line.startswith('# ') and line.strip().endswith(GROUP_NAME_SUFFIX):
            cutLines.append(ln)

    return sorted(cutLines), is_multiline
