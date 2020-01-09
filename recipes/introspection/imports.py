# std libs
import io
import ast
import sys
import math
import itertools as itt
from functools import partial
from collections import defaultdict

# third-party libs
from stdlib_list import stdlib_list
from anytree import Node, RenderTree

# from importlib.machinery import PathFinder


# list of builtin modules
easterEggs = ['this', 'antigravity']
unlisted = ['keyword']  # auto-generated module for builtin keywords
builtin_module_names = stdlib_list(sys.version[:3]) + easterEggs + unlisted

# object that finds system location of module from name
# pathFinder = PathFinder()

# internal sorting codes
MODULE_GROUP_NAMES = ['std', 'third-party', 'local', 'relative']

# list of local module names
# TODO: this in separate file
LOCAL_MODULES = ['obstools', 'graphical', 'pySHOC', 'recipes', 'tsa', 'mCV',
                 'motley', 'salticam']


# FIXME: this weird gotcha:
# import logging
# import logging.config # THIS WILL GET REMOVED!
# logging.config

# TODO: unit tests!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# TODO: local import that are already in global namespace


def null(_):
    return 0


def echo(_):
    return _


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


def isAnyImport(st):
    return isinstance(st, (ast.ImportFrom, ast.Import))


def get_module_typecode(module_name):
    if isAnyImport(module_name):
        module_name = get_module_names(module_name, depth=0)

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


def get_module_names(node, split=True, depth=None):
    # get the module name from an Import or ImportFrom node. Assumes one
    # module per statement
    if not split:
        depth = None
    if depth:
        split = True

    if depth is 0:
        idx = 0
    else:
        idx = slice(depth)

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
            TypeError(f'Encountered `import {", ".join(names)}`.' +
                      'Please split single line, multi-module import '
                      'statements first.  This can be done by using '
                      '`ImportCapture(split=True).visit(ast.parse(source_code)`'
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


def print_imports_tree(tree, ws=50):
    """
    Print a representation of the tree along with the statements at each leaf

    Parameters
    ----------
    tree

    Returns
    -------

    """
    for pre, _, node in RenderTree(tree, childiter=sort_nodes):
        # lvl = len(pre) // 4
        # stm = str(getattr(node, 'order', '')) + ' ' + getattr(node, 'stm', '')
        stm = getattr(node, 'stm', '')
        if '\n' in stm:
            stm = stm.replace('\n',
                              '\n' + pre[:-4] + ' ' * (len(str(node.name)) + 4))
        pre = f'{pre}{node.name}'
        w = ws - len(pre)
        print(f'{pre}{stm: >{w + len(stm)}s}')


def print_imports_tree2(tree, ws=50):
    print(RenderTree(tree).by_attr('stm'))


def write_imports_tree(stream, tree, headers=True, suffix='libs'):
    for pre, _, node in RenderTree(tree, childiter=sort_nodes):
        lvl = len(pre) // 4
        if lvl == 1 and headers:
            # commented header for import group
            write_line(stream, f'\n# {node.name} {suffix}')

        if hasattr(node, 'stm'):
            write_line(stream, node.stm)
            # separate groups by newline


def write_line(s, line):
    s.write(line)
    s.write('\n')


def write_lines(s, lines):
    for line in lines:
        write_line(s, str(line))  # str convert won't be needed if you make
        # ImportStatement str subclass


class _FunkyDict(dict):
    def get(self, key, default=''):
        return dict.get(self, key, default)


class Funky(object):
    # Helper class for creating the lower branches of the tree (grouping
    # submodules)
    # basically a hack to create functions that
    def __init__(self, statements):
        names = map(get_module_names, statements)
        self.subs = [_FunkyDict({s: su for s, su in zip(statements, sub) if su})
                     for sub in itt.zip_longest(*names)]
        # dict(zip(statements, sub))
        self.max_depth = len(self.subs)

    def __getitem__(self, key):
        return self.subs[key].get

    def __iter__(self):
        for i in range(self.max_depth):
            yield self[i]


# def depends_on(filename, up_to_line=None):  # TODO
#     code = get_block(filename, up_to_line)
#     tree = ast.parse(code)
#     visitor = ModuleExtractor()
#     visitor.visit(tree)
#     return visitor.modules

def get_style_groups(statements):
    # moduleNameCount = defaultdict(int)
    moduleIsFrom = defaultdict(list)

    # count how many times any given module is used in import
    # statements, and check whether there are ImportFrom style
    # imports for this module
    for node in statements:
        name = get_module_names(node)[0]
        # moduleNameCount[name] += 1
        moduleIsFrom[name].append(isinstance(node, ast.ImportFrom))

    # some logic on the ImportFrom statements to help with sorting.
    # Make groups for modules having
    #   0: only `import x` style;
    #   1: mixed styles: eg: `import x`; `from x.y import a`
    #   2: only  `from x import y` style
    return {m: any(b) + all(b)
            for m, b in moduleIsFrom.items()}


def make_branch(node, statements, funcs, sorts, lvl=0):
    func = funcs[lvl] if lvl < len(funcs) else None
    sorter = sorts[lvl] if lvl < len(sorts) else null
    for child, _, grp in _make_children(node, statements, func, sorter, lvl):
        # print(lvl, child, _, grp)
        make_branch(child, grp, funcs, sorts, lvl + 1)


def _make_children(node, statements, func, sort, lvl):
    statements = list(statements)

    if len(statements) == 1:
        # Deepest level. Leaf nodes get attributes here.
        # print('PING', lvl, rewrite(statements[0]))
        node.stm = rewrite(statements[0])
        node.order = min(len(node.stm), 80)

        # order groups by maximal statement length
        if lvl >= 3:
            node.order = min(len(node.stm), 80)
            parent = node.parent
            for _ in range(3, lvl):
                parent.order = max(node.order, parent.order)
                parent = parent.parent

        return

    else:
        statements.sort(key=func)
        for gid, stm in itt.groupby(statements, func):
            child = Node(gid, parent=node, order=sort(gid))
            yield child, gid, stm


def make_tree(statements, aesthetic=True, alphabetic=False, ):
    """"""

    # collect the import statements
    root = Node("body")

    # no import statements ?
    if len(statements) == 0:
        return root

    if aesthetic:
        # hierarchical group sorting for aesthetic
        importStyleGroups = get_style_groups(statements)

        def lvl1(stm):
            return importStyleGroups[get_module_names(stm, depth=0)]

        # decision functions
        groupers = [get_module_kind, lvl1, ] + list(Funky(statements))
        sorters = [MODULE_GROUP_NAMES.index, echo]

    elif alphabetic:
        raise NotImplementedError

    # make tree
    make_branch(root, statements, groupers, sorters)
    return root


def get_tree(source, up_to_line=math.inf, filter_unused=True,
             alphabetic=False, aesthetic=True, preserve_scope=True):
    # Capture import nodes
    split_multi_module = True
    net = ImportCapture(up_to_line, not preserve_scope, split_multi_module,
                        filter_unused)
    importsTree = net.visit(ast.parse(source))

    # group and sort (creates a new tree structure)
    return make_tree(importsTree.body, aesthetic, alphabetic), net


def get_tree_file(filename, up_to_line=math.inf, filter_unused=True,
                  alphabetic=False, aesthetic=True, preserve_scope=True):
    filename = str(filename)
    with open(filename) as fp:
        source = fp.read()

    root, captured = get_tree(source, up_to_line, filter_unused, alphabetic,
                              aesthetic, preserve_scope)
    return root


def tidy(filename, up_to_line=math.inf, filter_unused=True, alphabetic=False,
         aesthetic=True, preserve_scope=True, keep_multiline=True,
         headers=None, write_to=None, dry_run=False, report=False):
    """
    Tidy up import statements that might lie scattered throughout hastily
    written source code. Sort them, filter unused, group them, re-write them
    in the document header or write to a new file or just print the
    tidied code to stdout.


    Parameters
    ----------
    filename: str or Path
        input filename
    up_to_line: int
        line number for last line in input file that will be processed
    alphabetic: bool
        sort alphabetically
    aesthetic: bool
        sort aesthetically. The sorting rules are as follow:
        # TODO
    preserve_scope: bool
        Whether or not to move the import statements that are in a local scope
    headers: bool or None
        whether to print comment labels eg 'third-party libs' above different
        import groups.  If None (the default) this will only be done if there
        are imports from multiple groups.
    write_to: str or Path
        output filename
    dry_run: bool
        if True, don't edit any files, instead return the re-shuffled source
        as a string.

    Returns
    -------
    sourceCode: str
        Reformatted source code as a str.
    """
    # todo: style preference: "import uncertainties.unumpy as unp" over
    #                         "from uncertainties import unumpy as unp"

    # fixme: keep multiline imports as multiline

    #
    filename = str(filename)
    with open(filename) as fp:
        source = fp.read()

    # output
    write_to = write_to or filename  # default is to overwrite input file

    if dry_run:
        stream = io.StringIO()
    else:
        # FIXME: any error that occurs in `_tidy` may leave input file in a
        #  weird state, or even erase all data? Especially errors with code
        #  that cannot be parsed due to syntax errors.  TEST FOR THIS!!
        # FIXME: have to ensure file closes properly when error, also not get
        #  erased   !!!
        stream = open(write_to, 'w')

    _tidy(source, stream, up_to_line, filter_unused, alphabetic, aesthetic,
          preserve_scope, keep_multiline, headers, report)

    s = None
    if dry_run:
        s = stream.getvalue()

    # closing
    stream.close()

    # if report: # TODO checkout difflib
    #     print('-' * 160)
    #     print(filename)
    #     print('-' * 160)

    return s


def tidy_source(source, up_to_line=math.inf, filter_unused=True,
                alphabetic=False, aesthetic=True, preserve_scope=True,
                keep_multiline=True, headers=None, report=False):
    #
    with io.StringIO() as output_stream:
        _tidy(source, output_stream, up_to_line, filter_unused, alphabetic,
              aesthetic, preserve_scope, keep_multiline, headers, report)
        return output_stream.getvalue()


def _tidy(source, output_stream, up_to_line=math.inf, filter_unused=True,
          alphabetic=False, aesthetic=True, preserve_scope=True,
          keep_multiline=True, headers=None, report=False):
    #
    root, captured = get_tree(source, up_to_line, filter_unused, alphabetic,
                              aesthetic, preserve_scope)
    # at this point the import statements should be grouped and sorted
    # correctly in new tree
    if report:
        print_imports_tree(root)

    if len(root.children) == 0:
        # no imports
        output_stream.write(source)
        return

    # create new source code with import statements re-shuffled
    # group headings
    if headers is None:
        headers = (len(root.children) > 1)

    # line list. might be slow for large codebase
    lines = source.splitlines()

    # get line numbers for removal
    cutLines, _ = excision_flagger(lines, captured.line_nrs)

    # write the document header
    write_lines(output_stream, lines[:cutLines[0]])

    # FIXME: too many newlines after imports

    # write the ordered import statements (render the tree!)
    write_imports_tree(output_stream, root, headers)

    # finally rebuild the remaining source code, omitting the previously
    # extracted import lines
    for i, line in enumerate(lines):
        if (i >= cutLines[0]) and (i not in cutLines):
            write_line(output_stream, line)


def line_sort(line):
    return line.startswith('from'), len(line)


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
        if line.startswith('# ') and line.strip().endswith('libs'):
            cutLines.append(ln)

    return sorted(cutLines), is_multiline


def accumulate(a, start=0):
    """Generator that yields cumulative sum of elements of the input iterable"""
    tot = int(start)
    for item in a:
        tot += item
        yield tot


def rewrite(node, width=80):
    """write an import node as str"""
    s = ''
    if isinstance(node, ast.ImportFrom):
        # for module relative imports, `node.module` holds the sub-module
        relative = '.' * node.level
        module = ''.join((relative, node.module or '')).strip()
        s = 'from %s ' % module

    # write the aliases
    s += 'import '
    last = len(node.names) - 1
    aliases = [' as '.join(filter(None, (alias.name, alias.asname)))
               + [', ', ''][(i == last)]
               for i, alias in enumerate(node.names)]

    # check length
    lengths = list(map(len, aliases))
    length = len(s) + sum(lengths)

    if length <= width:
        s += ''.join(aliases)
    else:  # split lines
        # wrap imported names in a tuple
        s += '('
        mark = len(s)
        for i, l in enumerate(accumulate(lengths, len(s))):
            if l > width:
                # go to next line & indent to tuple mark
                s = s.strip()
                s += '\n' + ' ' * mark
            s += aliases[i]
        s += ')'
    return s


def remove_unused_names(node, unused):
    i = 0
    j = len(node.names)
    while i < j:
        alias = node.names[i]
        if (alias.asname in unused) or (alias.name in unused):
            r = node.names.pop(i)
            # print('removing', r.name, r.asname, 'since',
            #       ['alias.asname in unused',
            #        'alias.name in unused'][(alias.name in unused)])
            j -= 1
        i += 1

    if len(node.names):
        return node


def merge_duplicates(stm):
    # assume sorted already
    # combine separate statements that import from the same module
    stm = sorted(stm, key=partial(get_module_names, split=False))

    r = []
    prev = None
    for i, st in enumerate(stm):
        if i and isinstance(st, ast.ImportFrom) and \
                isinstance(prev, ast.ImportFrom) and \
                (st.module == prev.module):
            names = set(_.name for _ in prev.names)
            for alias in st.names:
                if alias.name not in names:
                    prev.names.append(alias)
            continue

        r.append(st)
        prev = st

    return r


# def _gen_node_names(node):
#     if len(node.names):
#         for alias in node.names:
#             if alias.asname:
#                 yield alias.asname
#             else:
#                 yield alias.name
#     else:
#         yield node.module  # not sure if this is ever reached


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


class ImportCapture(ast.NodeTransformer):

    # TODO: scope aware capture

    def __init__(self, up_to_line=math.inf, capture_local=True, split=True,
                 filter_unused=True, merge_duplicates=True):
        #
        self.up_to_line = up_to_line  # internal line nrs are 1 base
        self.indent_ok = 0  # any indented statement will be ignored
        if bool(capture_local):
            self.indent_ok = math.inf  # all statements will be captured

        self.split = bool(split)
        self.filter_unused = bool(filter_unused)
        self.merge_duplicates = bool(merge_duplicates)
        #
        self.used_names = set()
        self.imported_names = []
        self._current_names = []
        self.line_nrs = []

        # self.module_name_counts = defaultdict(int)

    def _should_capture(self, node):
        return (node.lineno <= self.up_to_line) and \
               (node.col_offset <= self.indent_ok)

    def visit_Module(self, node):

        if self.filter_unused and (self.up_to_line < math.inf):
            raise ValueError('With `up_to_line` given and finite, cannot '
                             'determine complete list of used names in module.')

        # first call to `generic_visit` will build the tree as well as capture
        # all the  imported names and used names
        module = self.generic_visit(node)

        # next filter stuff we don't want
        new_body = []
        i = -1
        for node in module.body:
            # filter everything that is not an import statement
            if isAnyImport(node):
                i += 1
            else:
                continue

            if self.filter_unused:
                # filter unused import statements here
                inames = self.imported_names[i]
                unused = set(inames) - self.used_names
                if len(unused) == len(node.names):  #
                    continue  # this statement not captured

                if len(unused) < len(node.names):
                    # deal with `from x.y import a, b, c`
                    # style imports where some imported names are unused
                    if isinstance(node, ast.ImportFrom):
                        remove_unused_names(node, unused)

            # print('append', node)
            new_body.append(node)

        if self.merge_duplicates:
            new_body = merge_duplicates(new_body)

        return ast.Module(new_body)

    def visit_Import(self, node):
        node = self.generic_visit(node)
        if self._should_capture(node):
            # capture line numbers
            self.line_nrs.append(node.lineno - 1)

            # split 1 line multi-module statements like: `import os, re, this`
            if self.split and len(node.names) > 1:
                new_nodes = []
                for i, alias in enumerate(node.names):
                    new_node = ast.Import([ast.alias(alias.name, alias.asname)])
                    new_nodes.append(new_node)

                for _ in self._current_names:
                    self.imported_names.append([_])
            else:
                self.imported_names.append(self._current_names)  # extend?
                new_nodes = node

            self._current_names = []
            return new_nodes
        return node

    def visit_ImportFrom(self, node):
        node = self.generic_visit(node)
        if self._should_capture(node):
            # capture line numbers and imported names
            self.line_nrs.append(node.lineno - 1)
            self.imported_names.append(self._current_names)
            self._current_names = []
        return node

    def visit_alias(self, node):
        name = next(filter(None, (node.asname, node.name)))
        if name != '*':
            self._current_names.append(name)
            # starred imports are lame dude. #todo: emit warning??
        return node

    def visit_Name(self, node):
        self.used_names.add(node.id)
        return node
