"""
Refactor import statements in python source code.
"""


# std
import io
import ast
import math
import warnings as wrn
import functools as ftl
import itertools as itt
from pathlib import Path
from collections import defaultdict
from importlib.util import find_spec

# third-party
import more_itertools as mit
from loguru import logger

# relative
from ... import api, cosort, not_null, op, user_packages, pprint as pp
from ...iter import unduplicate
from ...functionals import negate
from ...logging import LoggingMixin
from ...string import remove_prefix
from ...io import open_any, safe_write
from ...pprint.callers import describe
from ...config import ConfigNode, load_yaml
from ..utils import (BUILTIN_MODULE_NAMES, get_module_name, get_package_name,
                     get_stream, is_script)


# ---------------------------------------------------------------------------- #
# FIXME: unscoped imports do not get added to top!!!
# FIXME: inline comments get removed

# TODO: comment directives to keep imports ?
# TODO: split_modules
# TODO: style preference: "import uncertainties.unumpy as unp" over
#                         "from uncertainties import unumpy as unp"
# TODO: local import that are already in global namespace

# TODO: sort by submodule width?

# TODO: merge these
# from collections.abc import Hashable
# from collections import OrderedDict, UserDict, abc, defaultdict

# TODO detect clobbered imports
# from x import y
# from y import y

# FIXME:
# import ast, warnings
# import math
# import warnings as wrn

# FIXME:  THIS WAS A LIE!!
# This file is an initializer for a module: 'recipes'
# Only imports from the standard library will be filtered.

# ---------------------------------------------------------------------------- #
CONFIG = ConfigNode.load_module(__file__, 'yaml')

# warning control
if CONFIG.log_warnings:
    # _original_showwarning = wrn.showwarning

    def showwarning(message, *args, **kws):
        logger.warning(message)
        # _original_showwarning(message, *args, **kws)

    wrn.showwarning = showwarning

# ---------------------------------------------------------------------------- #
# module constants
api_synonyms = api.synonyms({
    'filter':          'filter_unused',
    'relative(_to)?':  'relativize',
    'module_name':     'relativize'
})


# supported styles for sorting
STYLES = ('alphabetic', 'aesthetic')

# USER_PACKAGES_DB = Path.home() / '.config/recipes/local_libs.txt'
USER_PACKAGES = load_yaml(user_packages)['local']


# ---------------------------------------------------------------------------- #
# Functions for sorting / rewriting import nodes


def is_import(node):
    return isinstance(node, ast.Import)


def is_import_from(node):
    return isinstance(node, ast.ImportFrom)


def is_any_import_node(node):
    return isinstance(node, (ast.ImportFrom, ast.Import))


def is_wildcard(node):
    return is_import_from(node) and node.names[0].name == '*'


def is_relative(node):
    return get_level(node) > 0


def get_level(node):
    """Get the level of an import node. Positive for relative imports else 0."""
    return getattr(node, 'level', 0)


def get_length(node):
    """Get line width of the import statement as it would appear in source."""
    return len(rewrite(node))


def get_module_name_list(node):
    return get_module_name(node).split('.')


def relative_sorter(node):
    # this prioritizes higher relatives '..' above '.'
    # also '..' above '..x'
    return (0.5 * bool(node.module) - node.level) if is_relative(node) else 0


def expand_wildcards(node, module=None):

    if not is_wildcard(node):
        return node

    if module is None and is_relative(node):
        raise ValueError('Module required for resolving wildcard inports.')

    module = module or node.module
    if (spec := find_spec(module)):
        names = get_defined_names(spec.origin)
        node.names = list(map(ast.alias, names))
    else:
        logger.warning('Could not find module to expand wildcards: {!r}.', module)

    return node


def get_defined_names(file):

    source = Path(file).read_text()
    module = ast.parse(source)
    captured = DefinedNames()
    module = captured.visit(module)

    names = set()
    names.update(*captured.used_names.values())

    return [name for name in names if not name.startswith('_')]


# ---------------------------------------------------------------------------- #
# Node writer

def rewrite(node, width=80, hang=None, indent=4, one_per_line=False):
    """write an import node as str"""
    s = ''
    if isinstance(node, ast.ImportFrom):
        # for module relative imports, `node.module` holds the sub-module
        s = f'from {"." * node.level}{node.module or ""} '

    # write the aliases
    s += 'import '
    aliases = [
        f'{alias.name}{f" as {alias.asname}" if alias.asname else ""}, '
        for alias in unduplicate(node.names, op.attrgetter('name', 'asname'))
    ]
    aliases[-1] = aliases[-1].rstrip(', ')

    # check length
    lengths = list(map(len, aliases))

    # mark, *splitx = itt.accumulate(map(len, aliases), initial=len(s))

    if (total := len(s) + sum(lengths)) <= width:
        return ''.join((s, *aliases))

    # split lines
    if hang is None:
        # hang modules on line below if they will span more than 2 lines if not
        # hung. This is the natural, space optimal choice.
        right_space = width - len(s)
        hang = (((total // right_space) > 2)
                or any(l > right_space for l in lengths))

    # wrap imported names in a tuple
    s += '(' + ('\n' + (' ' * indent)) * hang
    start = mark = indent if hang else len(s)
    nl = f'\n{"":<{start}}'
    for i, l in enumerate(lengths):
        # print(aliases[i], mark, l,  mark + l > width)
        if (i and one_per_line) or (mark + l > width):
            # go to next line & indent to tuple mark
            s = s.strip() + nl
            mark = start

        s += aliases[i]
        mark += l

    s += ')'  # ('\n' * hang + ')')
    return s


# ---------------------------------------------------------------------------- #
# Group sorters

def is_builtin(name):  # name.split('.')[0]
    return name in BUILTIN_MODULE_NAMES


def is_local(name):
    return name in USER_PACKAGES


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


def get_module_type(module_name):
    return CONFIG.module_group_names[get_module_typecode(module_name)]


def get_module_typecode(module_name):

    # get name if Node
    if is_any_import_node(module_name):
        module_name = get_package_name(module_name)
    #
    assert isinstance(module_name, str)

    if is_builtin(module_name):
        return 0

    if is_local(module_name):
        return 2

    # sourcery skip: assign-if-exp, reintroduce-else
    if not module_name or module_name.startswith('.'):
        return 3

    return 1
    # if is_3rd_party(module_name):
    #     return 1


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


def alias_sorter(alias):
    """
    Aliases are sorted in case-sensitive alphabetical order.
    UPPERCASE preceeds TitleCase preceeds lowercase.
    """
    return (alias.asname is not None,  # "import x as y" after "import whatever"
            not alias.name.isupper(),
            alias.name,
            alias.name.islower())


# Group import statements
GROUPERS = (get_module_typecode,
            get_package_name,
            # get_level
            )

# Order the groups wrt each other
GROUP_SORTERS = (get_group_style,
                 get_group_size,
                 get_group_width)

# Order the statements within groups
NODE_SORTERS = {
    'aesthetic': (get_module_typecode,
                  is_import_from,
                  relative_sorter,
                  get_length,
                  get_module_name
                  ),
    'alphabetic': (get_module_typecode,
                   is_import_from,
                   relative_sorter,
                   get_module_name,
                   get_length
                   )
}


# ---------------------------------------------------------------------------- #
# Node Transformers

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
    """
    Sets node `parent` attribute. For consistency, module parent is set to
    `None`.
    """

    parent = None

    def visit(self, node):
        logger.trace('\n{} parent set to {}.', node, self.parent)
        node.parent = self.parent
        self.parent = node
        new = super().visit(node)
        self.parent = new.parent if isinstance(new, ast.AST) else node.parent
        logger.trace('\nParentage is now {}.', self.parent)
        return new


class NameCapture(Parentage):

    def __init__(self):
        self.parent = None
        self.used_names = defaultdict(set)


class UsedNames(NameCapture):

    def visit_Name(self, node):
        node = self.generic_visit(node)
        self.used_names[node.parent].add(node.id)
        return node

    def visit_Attribute(self, node):
        node = self.generic_visit(node)
        if isinstance(node.value, ast.Name):
            self.used_names[node.parent].add(f'{node.value.id}.{node.attr}')
        return node


class DefinedNames(NameCapture):

    def __init__(self, scope=ast.Module, keep_private_names=False):

        super().__init__()

        assert issubclass(scope, ast.AST)
        self.scope = scope
        self.no_private_names = not bool(keep_private_names)

    def _capture(self, node):
        node = self.generic_visit(node)
        if isinstance(node.parent, self.scope):
            if node.name.startswith('_') and self.no_private_names:
                return node

            # capture
            self.used_names[node.parent].add(node.name)

        return node

    def visit_ClassDef(self, node):
        return self._capture(node)

    def visit_FunctionDef(self, node):
        return self._capture(node)


class ImportCapture(UsedNames):
    def __init__(self, up_to_line=math.inf):
        super().__init__()
        self.up_to_line = up_to_line or math.inf  # internal line nrs are 1 base
        self.line_nrs = []
        self.imported_names = defaultdict(set)

    def _should_capture(self, node):
        return (node.lineno <= self.up_to_line) and (node.col_offset == 0)

    # def visit_Module(self, node):
    #     # first call to `generic_visit` will build the tree as well as capture
    #     # all the  imported names and used names
    #     return self.generic_visit(node)

    def visit_Import(self, node):
        node = self.generic_visit(node)
        if not self._should_capture(node):
            return node

        # capture line numbers
        self.line_nrs.append(node.lineno - 1)
        return node

    visit_ImportFrom = visit_Import

    def visit_alias(self, node):
        name = node.asname or node.name
        if name != '*':
            self.imported_names[node.parent.parent].add(name)
        return node


class ImportFilter(Parentage):
    def __init__(self, names=(), ):
        self.remove = set(names)

    def visit_Import(self, node):
        node = self.generic_visit(node)
        if node.names:
            return node

        # if all aliases were removed, import node is filtered from tree
        logger.debug('Filtering empty import node (all aliases filtered).')

    #
    visit_ImportFrom = visit_Import

    def visit_alias(self, node):
        node = self.generic_visit(node)

        if node.name in self.remove:
            logger.info('Removing import: {:s}.', node.name)
            return  # entire node filtered

        if node.asname in self.remove:
            logger.info('Removing alias {:s} to imported name {:s}.',
                        node.asname, node.name)
            node.asname = None

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


class WildcardExpander(Parentage):

    def __init__(self, module):
        self.module = module

    def visit_ImportFrom(self, node):
        node = self.generic_visit(node)

        if not is_wildcard(node):
            return node

        # relative
        if node.level:
            parts = self.module.split('.')
            module = '.'.join((*parts[:(1 - node.level) or None], node.module))
        else:
            module = self.module

        return expand_wildcards(node, module)


class ImportMerger(ImportFilter):
    # combine separate statements that import from the same module
    # >>> from x import y
    # >>> from x import z
    # becomes
    # >>> from x import y, z

    def __init__(self, level=1):
        super().__init__()
        self.aliases = defaultdict(dict)

    def visit_Import(self, node):
        if super().visit_Import(node) is None:
            return

        # don't merge anything with >>> from ... import *
        if is_wildcard(node):
            return node

        # scope : Module or FunctionDef etc containing import
        scope = node.parent
        module_name = get_module_name(node)
        aliases = self.aliases[scope]
        # logger.debug(f'\n{self.__class__}\n{module_name = }; {node = }; {scope = }')
        #  f'\n{os.linesep.join(map(rewrite, scope.body))}')

        # avoid duplicates >>> from x import y, y
        if module_name not in aliases:
            # new module encountered
            aliases[module_name] = node
            return node

        # already encountered module_name in scope
        existing_node = aliases[module_name]

        # Existing module: extend aliases for that node, and filter the current
        # existing_node.names.append(node)
        aliases = list(unduplicate([*existing_node.names, *node.names],
                                   op.attrgetter('name', 'asname')))

        if aliases != existing_node.names:
            existing_node.names = aliases
            logger.opt(lazy=True).debug('Merged imports with same module {!r}',
                                        lambda: rewrite(existing_node))

        # we are about to visit the aliases, so ensure that `Parentage` sets the
        # alias parents to the previously `existing_node` import node which we
        # just extended. This is also important for correctly scoping the
        # imports at module level.
        node.parent = existing_node.parent
        # dont return anything => filter this `node` since we have a previously
        # `existing_node`

    #
    visit_ImportFrom = visit_Import


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
    def __init__(self, parent_module_name):
        """
        Transform import statements to relative style imports inside
        module with fullname `module_name`.

        Parameters
        ----------
        module_name : str
            Dot separated name of the parent module or package.
            eg: 'awesome.code'


        Examples
        --------
        >>> module = ImportRelativizer('awesome.code').visit(
        ...    ast.parse('from awesome.code.magic import levitation')
        ... )
        ... rewrite(module.body[0])
        'from ..magic import levitation'
        """
        module_name = str(parent_module_name)
        # package, *submodules
        self.parts = module_name.split('.')
        self.level = len(self.parts)
        self.sublevels = dict(map(reversed, enumerate(self.parts[::-1], 1)))
        parents = itt.accumulate(self.parts, '{}.{}'.format)
        self.absolute = dict(enumerate(list(parents)[::-1], 1))

    def visit_ImportFrom(self, node):
        node = self.generic_visit(node)
        module = node.module

        if not module:
            # a top-level relative import
            return node

        if node.level > len(self.parts):
            wrn.warn(f'Relative import beyond top level: {rewrite(node)!r}')
            return node

        if node.level:
            # de-relativize first. Sometimes allows shortening: ..c -> .
            module = '.'.join((self.absolute[node.level], module))

        # replace module with relative
        # a         ->      ...
        # a.b       ->      ..
        # a.b.c     ->      .
        # AND
        # ...b      ->      ..
        # ...b.c    ->      .
        # ..c       ->      .
        # HOWEVER
        # .c        ->      .c
        # since it implies the existence of c/c.py
        for lvl, parent in self.absolute.items():
            if module.startswith(parent):
                node.module = remove_prefix(module, parent).lstrip('.') or None
                node.level = lvl
                break

        return node


class HandleFuncs:
    """Base class that checks that inputs are callable."""

    def __init__(self, *functions):
        for func in filter(negate(callable), functions):
            raise TypeError(f'Sorting {describe(func)} should be callable.')

        self.functions = functions

    def __call__(self, node):
        return tuple(func(node) for func in self.functions)


class ImportGrouper(HandleFuncs, ast.NodeVisitor):
    def __init__(self, *functions):
        super().__init__(*functions)
        self.groups = defaultdict(ftl.partial(ast.parse, ''))

    def visit_Import(self, node):
        gid = node.gid = self(node)
        self.groups[gid].body.append(node)

    #
    visit_ImportFrom = visit_Import

    def pprint(self):
        return pp.mapping(self.groups, '', brackets='', hang=True,
                          # lhs=GroupHeaders().get,
                          rhs=lambda _: '\n'.join(('', *_iter_import_lines(_))))


class ImportSorter(HandleFuncs, ast.NodeTransformer):  # NodeTypeFilter?
    # NodeTypeFilter(
    #     keep=(ast.Module, ast.Import, ast.ImportFrom, ast.alias)
    # )

    def visit_Import(self, node):
        node = self.generic_visit(node)
        node.order = self(node)
        node.names = sorted(node.names, key=alias_sorter)
        return node
    #
    visit_ImportFrom = visit_Import

    def visit_Module(self, node):
        node = self.generic_visit(node)
        node.body = sorted(node.body, key=op.attrgetter('order'))
        return node


# class ImportWriter(ast.NodeVisitor):
#     def __init__(self):
#         self.lines = []

#     def visit_Import(self, node):
#         self.generic_visit(node)
#         self.text += f'\n{rewrite(node)}'
#         return node
# #
#      visit_ImportFrom = visit_Import

def _iter_import_lines(module, headers=None):
    # generate source code lines from ast.Module, including import group header
    # comments and empty lines.

    # group headings
    if headers is None:
        # module has more than one import node
        n_nodes = len(module.body)
        # more than one import group present
        gids = {*op.AttrVector('gid', default=None).filter(module.body)}
        n_groups = len(set(next(zip(*gids)))) if gids else 1
        #
        headers = (n_nodes > 1) and (n_groups > 1)
    #
    headers = GroupHeaders(*(() if headers else [()]))

    for node in module.body:
        if not is_any_import_node(node):
            # There are no import staetments (left)
            return

        yield from headers.next(node)
        yield rewrite(node)


class GroupHeaders:

    def __init__(self, names=CONFIG.groups.names, suffix=CONFIG.groups.suffix):
        self.names = dict(enumerate(names))
        self.suffix = str(suffix or '')
        self.newlines = mit.padded([''], '\n')

    def get(self, i):
        return f'# {self.names[i]} {self.suffix}'.rstrip()

    def next(self, node):
        gid = getattr(node, 'gid', [-1])[0]
        if name := self.names.pop(gid, ()):
            # pylint: disable=stop-iteration-return
            yield f'{next(self.newlines)}# {name} {self.suffix}'.rstrip()


# convenience functions
# ---------------------------------------------------------------------------- #

def depends_on(file_or_source):
    return ImportRefactory(file_or_source).get_dependencies()


@api_synonyms
def refactor(file_or_source,
             sort=CONFIG.sort,
             filter_unused=None,
             split=0,
             merge=1,
             expand_wildcards=True,
             relativize=None,
             #  unscope=False,
             headers=None
             ):

    # up_to_line=math.inf,
    # , keep_multiline=True,
    refactory = ImportRefactory(file_or_source)
    module = refactory.refactor(sort, filter_unused, split, merge,
                                expand_wildcards, relativize)
    return refactory.write(module, headers)


# aliases
tidy = refactor


def _parse_partial(source, max_remove=5):
    """
    Tenacious source code parsing, retrying with invalid syntax lines removed.
    """

    removed = []
    for i in range(max_remove + 1):
        try:
            module = ast.parse(source)
            if removed:
                logger.success('Parsed source code successfully after removing '
                               'lines: {}.', removed)
            return module, removed

        except SyntaxError as err:
            if i == 0:
                lines = source.splitlines()

            if i == max_remove:
                raise err

            logger.info('Could not parse source code due to {}. Removing line '
                        '{} and retrying.', err, err.lineno)

            # replace offending line with blank
            n = err.lineno - 1
            lines[n] = ''
            removed.append(n)
            source = '\n'.join(lines)


class ImportRefactory(LoggingMixin):
    """
    Tidy up import statements that might be scattered throughout hastily written
    source code. Sort them, filter unused or duplicate imports, group them by
    type, re-write them in the document header or write to a new file or just
    print the prettified code to stdout.
    """
    # up_to_line: int
    #     line number for last line in input file that will be processed

    @property
    def path(self):
        if self.filename:
            return Path(self.filename)

    def __init__(self, file_or_source):
        """
        Initialize the refactory for filename or source code.

        Parameters
        ----------
        file_or_source : str or Path
            Input filename or raw source code string.

        Examples
        --------
        >>> 
        """

        with open_any(get_stream(file_or_source)) as file:
            self.source = file.read()

        self.filename = None
        if isinstance(file, io.TextIOWrapper):
            self.filename = file.buffer.name

        # parse
        module, self.invalid_syntax_lines = _parse_partial(self.source)

        self.captured = ImportCapture()  # TODO: move inside filter_unused
        self.module = self.captured.visit(module)

        # save original module content so we can check if any changes were made
        self._original = ast.dump(self.module)

    def __call__(self, *args, **kws):
        module = self.refactor(*args, **kws)
        return self.write(module)

    def __repr__(self):
        if path := self.path:
            return f'{self.__class__.__name__}({path.name!r})'
        return f'{self.__class__.__name__}(<SourceCodeString>)'

    @api_synonyms
    def refactor(self,
                 sort=CONFIG.sort,
                 filter_unused=None,
                 split=0,
                 merge=1,
                 expand_wildcards=True,
                 relativize=None,
                 #  delocalize=False,
                 ):
        """
        Refactor import statements in python source code.

        Parameters
        ----------
        sort : str, {'aesthetic', 'alphabetically'}, optional
            The sorting rules are as follow: # TODO
        filter_unused : bool, optional
            Filter import statements for names that were not used in the source
            code. Default action is to filter unused imports only when the input
            source has some code beyond the import block, and is not a module
            initializer (`__init__.py`) script.
        split : {None, False, 0, 1}, optional
            Whether to split import statements:
            * Case `False` or `None`, do not
              split any import lines. * Case `0`, the default: Split single-line
              import statements involving multiple modules eg:
              >>> import os, re
                becomes
              >>> import os
              ... import re
            * Case `1`: Split single-line import statements involving any sub
              modules eg: 
              >>> from collections.abc import Sized, Collection
                becomes
              >>> from collections.abc import Sized
              ... from collections.abc import Collection
        merge : int, optional
            How to merge multiple import statements if at all, by default 1.
            This performs the inverse operation of `split`.
            * Case `False` or `None`, do not merge any import lines. 
            * Case `0`, the default: Merge multi-line import statements from the
              standard library: 
              >>> import os ... import re
                becomes
              >>> import os, re
            * Case `1`: Merge multiple import statements involving the same
              (sub)modules eg: 
              >>> from collections.abc import Sized
              ... from collections.abc import Collection
                becomes
              >>> from collections.abc import Sized, Collection
        relativize : str, optional
            The name of the module containing the import statements. Providing
            this will convert absolute module names to '.' where appropriate for
            the provided name. The default is None, which does relativization
            only if the parent module name can be discovered automatically, ie.
            if the class was initialized from a file and not a source code
            string, and that file is not a test or an executable script.


        Examples
        --------
        >>> ImportRefactory('import this, antigravity').refactor()
        import this
        import antigravity


        Returns
        -------
        ast.Module
            The refactored module.
        """

        # keep_multiline=True,
        #  up_to_line=math.inf,
        # sort

        # unscope: bool
        #     Whether or not to move the import statements that are in a local
        #     scope
        # headers: bool or None
        #     whether to print comment labels eg 'third-party' above different
        #     import groups. If None (the default) this will only be done if there
        #     are imports from multiple groups.

        module = self.module
        path = repr(str(self.path)) if self.path else 'source code'

        # check if there are any import statements
        if not self.captured.line_nrs:
            self.logger.info('No import statements in {}.', path)
            return module

        # if unscope:
        #     module = self.unscope(module)

        if expand_wildcards:
            module = self.expand_wildcards(module)

        # filter_unused = (self.up_to_line == math.inf and bool(used_names))
        if filter_unused is None:
            filter_unused = self._should_filter()

        if filter_unused:
            module = self.filter(module)

        if not_null(merge):
            module = self.merge(module, merge)

        if not_null(split, [0]):
            module = self.split(module, split)

        if relativize is None:
            relativize = (self.filename is not None)

        if relativize:
            module = self.relativize(module, relativize)
            # need to merge again in case some imports relativized to an
            # existing module
            if not_null(merge):
                module = self.merge(module, merge)

        delocalize = False
        if delocalize:
            # TODO
            module = self.delocalize(module)
        else:
            module = NodeScopeFilter(0).visit(module)

        if sort:
            module = self.sort_and_group(module, sort)

        if module == self.module:
            logger.info('Import statements in {} are already well sorted for '
                        '{!r} style!', path, sort)

        return module

    def sort_and_group(self, module=None, style=CONFIG.sort):
        """Sort and group."""

        module = module or self.module

        if not module.body:
            return module

        # group and sort
        grouper = ImportGrouper(*GROUPERS)
        grouper.visit(module)
        groups = {g: self.sort(mod, style)
                  for g, mod in grouper.groups.items()}

        if not groups:
            return module

        # reorder the groups
        modules = groups.values()
        typecodes, *_ = zip(*groups.keys())

        group_order = (map(f, modules) for f in GROUP_SORTERS)
        _, (module, *modules) = cosort(zip(typecodes, *group_order), modules)

        for mod in modules:
            module.body.extend(mod.body)

        return module

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
        return set(map(get_package_name, imports_only))

    def _should_filter(self):
        if len(self.captured.used_names) == 0:
            self.logger.info('Not filtering unused statements for import-only '
                             'script, since this would leave an empty file.')
            return False

        # if self.invalid_syntax_lines:
        #     self.logger.info('Not filtering unused statements for source code ')
            # 'containing syntax errors.')

        return True

    def filter_unused(self, module=None):
        module = module or self.module
        imported_names = self.captured.imported_names[module]
        used_names = set().union(*self.captured.used_names.values())
        # used_names = self.captured.used_names[module]
        unused = set.difference(imported_names, used_names)

        # is_init_file =
        if self.path and (self.path.name == '__init__.py'):
            self.logger.info(
                "This file is an initializer for a module: '{}'\n"
                "Only imports from the standard library will be filtered.",
                get_module_name(self.path)
            )
            # {u for u in unused if get_module_typecode(u) == 0}
            unused = set(filter(negate(get_module_typecode), unused))

        if imported_names and not self.captured.used_names:
            wrn.warn(
                'Filtering unused imports requested for source that contains no'
                ' code statements (besides imports). This will remove all '
                'import statements from the source, which is probably not what '
                'you intended. Please use `filter_unused=False` if you only '
                'wish to sort existing import statements.'
            )

        return ImportFilter(unused).visit(module)

    # alias
    filter = filter_unused

    def expand_wildcards(self, module):
        module = module or self.module
        name = get_module_name(self.path)
        return WildcardExpander(name).visit(module)

    def merge(self, module=None, level=1):
        module = module or self.module
        return ImportMerger(level).visit(module)

    def split(self, module=None, level=0):
        module = module or self.module
        return ImportSplitter(level).visit(module)

    def relativize(self, module=None, parent_module_name=None, level=None):
        module = module or self.module

        # check if we should try relativize. Excludes test files. Raise if
        # running from str source and no package or module name given.
        if not self._should_relativize(parent_module_name):
            return module

        # get the package name so we can replace
        # >>> from package.module import x
        # with
        # >>> from .module import x
        if parent_module_name in (None, True):
            if self.filename is None:
                # warning was emitted above, now we can just return unaltered
                # module
                return module

            try:
                parent_module_name = get_module_name(self.filename)
                if parent_module_name:
                    parent_module_name, *script = parent_module_name.rsplit('.', 1)
                    logger.info("Discovered parent module name: {!r} for file '{}'.",
                                parent_module_name, Path(self.filename).name)
            except ValueError as err:
                if (msg := str(err)).startswith(s := 'Could not get package name'):
                    logger.warning(
                        msg.replace(s, f'{s}. Skipping import relativization')
                    )
                    return module
                raise err from None

        if self._should_relativize(parent_module_name):
            return ImportRelativizer(parent_module_name).visit(module)

        return module

    def _should_relativize(self, parent_module_name):
        if parent_module_name not in (None, True):
            if not isinstance(parent_module_name, str):
                raise TypeError(
                    f'Invalid type for `parent_module_name`, expected str, '
                    f'received {type(parent_module_name)}.'
                )
            return True

        # cannot relativize without filename
        if ((self.filename is None) and (parent_module_name is True)):
            wrn.warn(
                'Import relativization requested, but no parent module name '
                'provided. Since we are running from raw input (source code '
                'string), you must provide the dot-separated name of the parent'
                ' module of the source code via `relative="my.package.name"`.'
                ' Alternatively, if the source resides in a file, pass the '
                '`filename` parameter to the `refactor` method to relativize '
                'import statements in-place.'
            )
            return False

        emit = wrn.warn if parent_module_name else logger.info
        filetype = OK = object()
        if self.path.name.startswith('test_'):
            # pre = ''
            filetype = 'test file'

        if is_script(self.source):
            # pre
            filetype = 'executable script'

        if filetype is OK:
            return True

        emit(f'This looks like a {filetype}. Skipping relativize.')
        return False

    def sort(self, module=None, how=CONFIG.sort):
        logger.trace('Sorting imports in module {} using {!r} sorter.',
                     module, how)
        module = module or self.module
        imports_only = NodeTypeFilter(
            keep=(ast.Module, ast.Import, ast.ImportFrom, ast.alias)
        ).visit(module)

        how = how.lower()
        how = STYLES[op.index(STYLES, how, test=str.startswith)]
        return ImportSorter(*NODE_SORTERS[how]).visit(imports_only)

    # def localize(self):

    def delocalize(self):
        raise NotImplementedError

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
        yield from _iter_import_lines(module, headers)

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
        """
        Write new source code with import statements refactored.

        Parameters
        ----------
        module : _type_
            _description_
        filename: str or Path, optional
            The output filename.
        headers : _type_, optional
            _description_, by default None


        Returns
        -------
        source_code: str
            Reformatted source code.
        """

        # at this point the import statements should be grouped and sorted
        # correctly in new tree
        # if report:
        #     root.pprint()

        # module = module or self.module
        # overwrite input file if `filename` not given
        filename = filename or self.filename

        # check for changes
        if (len(module.body) == 0) or (ast.dump(module) == self._original):
            # no statements in module, or unchange module- nothing to write
            logger.info('File contents left unchanged.')
            return self if filename else self.source

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
    # TODO: i think this is now changed in python >3.8
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
        if is_group_header_comment(line):
            cutLines.append(ln)

    return sorted(cutLines), is_multiline


def is_group_header_comment(line):
    # RGX = re.compile(rf'# ({"|".join(CONFIG.groups.names)}) {CONFIG.groups.suffix}')
    return (
        line.startswith('# ') and
        line[2:].startswith(tuple(CONFIG.groups.names)) and
        ((not (s := CONFIG.groups.suffix))
         or line.strip().endswith(s))
    )
