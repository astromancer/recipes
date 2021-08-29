
# std
import os
import io
import ast
import sys
import math
import inspect
import warnings as wrn
import functools as ftl
import itertools as itt
from pathlib import Path
from collections import defaultdict

# third-party
import more_itertools as mit
from stdlib_list import stdlib_list

# local
from recipes import cosort, op
from recipes.io import open_any
from recipes import pprint as pp
from recipes.functionals import negate
from recipes.string import replace_prefix, truncate
from recipes.logging import logging, get_module_logger

# relative
from ..io import safe_write


# FIXME: unscoped imports do not get added to top!!!
# FIXME: too many blank lines after module docstring


# TODO: split_modules
# TODO: style preference: "import uncertainties.unumpy as unp" over
#                         "from uncertainties import unumpy as unp"
# TODO: keep multiline imports as multiline
# TODO: local import that are already in global namespace
# TODO: sort aliases
# TODO: relativizing higher levels

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

# maximal filename size. Helps distinguish source code strings from filenames
F_NAMEMAX = os.statvfs('.').f_namemax


def is_import(node):
    return isinstance(node,  ast.Import)


def is_import_from(node):
    return isinstance(node,  ast.ImportFrom)


def is_any_import_node(node):
    return isinstance(node, (ast.ImportFrom, ast.Import))


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

def get_module_kind(module_name):
    return MODULE_GROUP_NAMES[get_module_typecode(module_name)]


def get_module_typecode(module_name):
    # get name if Node
    if is_any_import_node(module_name):
        module_name = get_mod_name0(module_name)
    #
    assert isinstance(module_name, str)

    if is_builtin(module_name):
        return 0
    if is_local(module_name):
        return 2
    if not module_name:  # module_name.startswith('.'):
        return 3
    return 1
    # if is_3rd_party(module_name):
    #     return 1


def is_builtin(name):  # name.split('.')[0]
    return name in builtin_module_names


def is_local(name):
    return name in LOCAL_MODULES


# ---------------------------------------------------------------------------- #
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


@ftl.singledispatch
def get_mod_name(node):
    # get the module name from an Import or ImportFrom node.
    raise TypeError()


@get_mod_name.register(ast.Import)
def _(node):
    # assert len(node.names) == 1
    return node.names[0].name


@get_mod_name.register(ast.ImportFrom)
def _(node):
    return f'{"." * node.level}{node.module or ""}'


def get_length(node):
    return len(rewrite(node))


def get_mod_name_list(node):
    return get_mod_name(node).split('.')


def get_mod_name0(node):
    return get_mod_name(node).split('.', 1)[0]


def get_group_style(module):
    # some logic on the ImportFrom statements to help with sorting.
    # Make groups for modules having
    #   0: only `import x` style;
    #   1: mixed styles: eg: `import x`; `from x.y import a`
    #   2: only  `from x import y` style
    isfrom = [isinstance(node, ast.ImportFrom) for node in module.body]
    return any(isfrom) + all(isfrom)


def get_group_width(module):
    return max(map(get_length, module.body))


def get_group_size(module):
    return len(module.body)


GROUPERS = (get_module_typecode,
            get_mod_name0)
GROUP_SORTERS = (get_group_style,
                 get_group_size,
                 get_group_width)
NODE_SORTERS = (get_module_typecode,
                is_import_from,
                get_length,
                get_mod_name,
                str)


class NodeTypeFilter(ast.NodeTransformer):
    def __init__(self, remove=(), keep=(ast.AST,)):
        self.keep = tuple(set(keep))
        self.remove = tuple(set(remove))

    def visit(self, node):
        if isinstance(node, self.keep) and not isinstance(node, self.remove):
            return super().visit(node)


class NodeScopeFilter(ast.NodeTransformer):
    def __init__(self, indent_ok=math.inf):
        self.indent_ok = indent_ok

    def ignore(self, node):
        return getattr(node, 'col_offset', -1) > self.indent_ok

    def visit(self, node):
        if not self.ignore(node):
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


class ImportFilter(ast.NodeTransformer):  #
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
            logger.debug('Removing import: %s', name)
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


class HandleFuncs:
    def __init__(self, *functions):
        for func in filter(negate(callable), functions):
            raise TypeError(f'Sorting function {func} should be callable.')

        self.functions = functions

    def __call__(self, node):
        return tuple(func(node) for func in self.functions)


class ImportGrouper(HandleFuncs, ast.NodeVisitor):
    def __init__(self, *functions):
        super().__init__(*functions)
        self.groups = defaultdict(ftl.partial(ast.parse, ''))

    def visit_any_import(self, node):
        gid = self(node)
        self.groups[gid].body.append(node)
        node.gid = gid
    #
    visit_Import = visit_ImportFrom = visit_any_import

    def pprint(self):
        return pp.mapping(self.groups, '', brackets='', hang=True,
                          # lhs=GroupHeaders().get,
                          rhs=lambda _: '\n'.join(('', *_iter_lines(_))))


class ImportSorter(HandleFuncs, ast.NodeTransformer):  # NodeTypeFilter?
    # NodeTypeFilter(
    #     keep=(ast.Module, ast.Import, ast.ImportFrom, ast.alias)
    # )

    def visit_any_import(self, node):
        node.order = self(node)
        return node
    #
    visit_Import = visit_ImportFrom = visit_any_import

    def visit_Module(self, node):
        node = self.generic_visit(node)
        node.body = sorted(node.body, key=op.attrgetter('order'))
        return node


# class ImportWriter(ast.NodeVisitor):
#     def __init__(self):
#         self.lines = []

#     def visit_any_import(self, node):
#         self.generic_visit(node)
#         self.text += f'\n{rewrite(node)}'
#         return node
# #
#     visit_Import = visit_ImportFrom = visit_any_import

def _iter_lines(module, headers=None):

    # group headings

    headers = (bool(headers) or
               # module has at least 2 import nodes
               ((len(module.body) > 1) and
                # more than one group present
                len({_.gid for _ in module.body}) > 1))
    headers = GroupHeaders(*(() if headers else [()]))

    for node in module.body:
        yield from headers.next(node)
        yield rewrite(node)


class GroupHeaders:
    def __init__(self, names=MODULE_GROUP_NAMES, suffix=GROUP_NAME_SUFFIX):
        self.names = dict(enumerate(names))
        self.suffix = str(suffix)
        self.newlines = mit.padded([''], '\n')

    def get(self, i):
        return f'# {self.names[i]} {self.suffix}'

    def next(self, node):
        gid = getattr(node, 'gid', [-1])[0]
        name = self.names.pop(gid, ())
        if name:
            # pylint: disable=stop-iteration-return
            yield f'{next(self.newlines)}# {name} {self.suffix}'


# convenience functions
# ---------------------------------------------------------------------------- #

def depends_on(file_or_source):
    return ImportRefactory(file_or_source).get_dependencies()


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


def refactor(file_or_source,
             sort='aesthetic',
             filter_unused=None,
             split=0,
             merge=1,
             relativize=True,
             #  unscope=False,
             headers=None,
             ):

    # up_to_line=math.inf,
    # , keep_multiline=True,
    refactory = ImportRefactory(file_or_source)
    module = refactory.refactor(sort, filter_unused, split, merge, relativize)
    return refactory.write(module, headers)


# aliases
tidy = refactor


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

        self.captured = ImportCapture()  # TODO: move inside filter_unused
        self.module = self.captured.visit(ast.parse(self.source))

    def __call__(self, *args, **kws):
        module = self.refactor(*args, **kws)
        return self.write(module)

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

    def filter_imports(self, module=None):
        return NodeTypeFilter(
            keep=(ast.Module, ast.Import, ast.ImportFrom, ast.alias)
        ).visit(module or self.module)

    def get_dependencies(self):
        imports_only = self.filter_imports()
        return set(map(get_mod_name0, imports_only))

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
        imports_only = NodeTypeFilter(
            keep=(ast.Module, ast.Import, ast.ImportFrom, ast.alias)
        ).visit(module)

        # sorters = get_mod_typecode, length_sort, get_mod_name, str
        # sorters = SORTING
        return ImportSorter(*NODE_SORTERS).visit(imports_only)

    # def localize(self):
    
    def delocalize(self):
        return 'TODO'

    def refactor(self,
                 sort='aesthetic',
                 filter_unused=None,
                 split=0,
                 merge=1,
                 relativize=True,
                #  delocalize=False,
                 ):
        #  unscope=False):
        # keep_multiline=True,
        #  up_to_line=math.inf,
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
        
        delocalize=False
        if delocalize:
            module = self.delocalize(module) # TODO
        else:
            module = NodeScopeFilter(0).visit(module)
        
        if sort is not None:
            if not module.body:
                return module

            # group and sort
            grouper = ImportGrouper(*GROUPERS)
            grouper.visit(module)
            groups = {g: self.sort(mod, sort)
                      for g, mod in grouper.groups.items()}

            # reorder the groups
            modules = groups.values()
            typecodes, *_ = zip(*groups.keys())
            group_order = (map(f, modules) for f in GROUP_SORTERS)
            _, (module, *modules) = cosort(zip(typecodes, *group_order),
                                           modules)

            for mod in modules:
                module.body.extend(mod.body)

        return module

    def _iter_lines(self, module=None, headers=None):  # keep_multiline=True
        # line generator to rewrite source code
        module = module or self.module

        # line list. might be slow for large codebase
        lines = self.source.splitlines()

        # get line numbers for removal
        (first, *cutLines), _ = excision_flagger(lines, self.captured.line_nrs)

        # write the document header
        yield from lines[:first]

        # write the ordered import statements (with group headings)
        yield from _iter_lines(module, headers)

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

    def write(self, module, filename=None, headers=None):
        # module=None,
        """

        write new source code with import statements refactored

        filename: str or Path
            output filename
        dry_run: bool
            if True, don't edit any files, instead return the refactored source
            as a string.

        Returns
        -------
        sourceCode: str
            Reformatted source code as a str.
        """

        # at this point the import statements should be grouped and sorted
        # correctly in new tree
        # if report:
        #     root.pprint()

        # module = module or self.module
        # overwrite input file if `filename` not given
        filename = filename or self.filename

        if len(module.body) == 0:
            # no imports - nothing to do
            if filename:
                return self
            return self.source

        # line generator
        lines = self._iter_lines(module, headers)

        # return the string if dry_run or reading from text stream
        if filename:
            safe_write(filename, lines)
            return self
        return '\n'.join(lines)


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
