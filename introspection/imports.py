import ast
import math
import os
import io
import sys
import itertools as itt
from collections import defaultdict
from importlib.machinery import PathFinder

from stdlib_list import stdlib_list

# list of builtin modules
easterEggs = ['this', 'antigravity']
builtin_module_names = stdlib_list(sys.version[:3]) + easterEggs

# object that finds system location of module from name
pathFinder = PathFinder()

# internal sorting codes
module_type_names = ['builtin', 'third-party', 'local', 'relative']

# list of local module names
LOCAL_MODULES = ['obstools', 'graphical', 'pySHOC', 'recipes', 'tsa', 'mCV',
                 'motley', 'slotmode']


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


def get_module_typecode(module_name):
    if is_builtin(module_name):
        return 0
    if is_local(module_name):
        return 2
    if module_name == '':
        return 3
    return 1
    # if is_3rd_party(module_name):
    #     return 1


def get_module_kind(module_name):
    return module_type_names[get_module_typecode(module_name)]


# def depends_on(filename, up_to_line=None):
#     code = get_block(filename, up_to_line)
#     tree = ast.parse(code)
#     visitor = ModuleExtractor()
#     visitor.visit(tree)
#     return visitor.modules


def write_line(s, line):
    s.write(line)
    s.write('\n')


def write_lines(s, lines):
    for line in lines:
        write_line(s, str(line))  # str convert won't be needed if you make
        # ImportStatement str subclass


def tidy(filename, up_to_line=math.inf, filter_unused=True, alphabetic=False,
         aesthetic=True, preserve_local_imports=True,
         headers=None, write_to=None, dry_run=False):
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
    preserve_local_imports: bool
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
    # todo: remove un-used imports

    # fixme: keep multiline imports as multiline
    filename = str(filename)
    with open(filename) as fp:
        source = fp.read()

    # line list. might be slow for large codebase
    lines = source.splitlines()

    # Reconstruct import lines + capture module names
    sourceTree = ast.parse(source)
    imEx = ImportExtractor(up_to_line, not preserve_local_imports)
    imEx.visit(sourceTree)

    # collect the statements that will be re-shuffled
    # if filter_unused:

    statements = imEx.statements

    # We have to be careful with multi-line imports since ast has no special
    # handling for these ito giving statement line end numbers. Lines ending on
    # the line continuation character '\', and lines containing multi-line
    # tuples are handled below
    cutLines = []
    for s in statements:
        ln = s.line_nr
        line = lines[ln]
        cutLines.append(ln)

        # line continuation
        while line.endswith('\\'):
            ln += 1
            line = lines[ln]
            cutLines.append(ln)
            # than  2 lines

        # multi-line tuple
        if '(' in line:
            while ')' not in line:
                ln += 1
                line = lines[ln]
                cutLines.append(ln)

    # count how many times a particular module is used in import statements,
    # and check whether there are ImportFrom style imports for this module
    moduleCount = defaultdict(int)
    moduleIsFrom = defaultdict(list)
    for s in statements:
        moduleCount[s.module] += 1
        moduleIsFrom[s.module].append(s.is_from)

    # get list of module names from which multiple objects are imported
    # repeated = [m for (m, cnt) in moduleCount.items() if cnt > 1 and m]
    # some logic on the ImportFrom statements to help with sorting
    moduleAnyFrom = {m: any(b) for m, b in moduleIsFrom.items()}
    moduleAllFrom = {m: all(b) for m, b in moduleIsFrom.items()}

    if aesthetic:
        # heirarchical group sorting for aesthetic
        # sorting function
        def grouper(s):
            name = s.module
            return get_module_typecode(name), name

        def sort_groups(item):
            key, statements = item
            _, name = key
            return (get_module_typecode(name),
                    moduleAllFrom.get(name, False),
                    # all statements are ImportFrom from this module
                    moduleAnyFrom.get(name, False),
                    max(map(len, map(str, statements))),
                    # fixme inherit from str
                    name.lower())
    elif alphabetic:
        raise NotImplementedError

    # divide statements into groups
    groups = defaultdict(list)
    for gid, grp in itt.groupby(statements, grouper):
        groups[gid].extend(grp)

    # at this point the import statements should be groups should be grouped
    # correctly. We still need to sort the groups in order as well as sort the
    # statements within each group.

    # create new source code with import statements re-shuffled
    write_to = write_to or filename  # default is to overwrite input file
    if dry_run:
        newSource = io.StringIO()
    else:
        newSource = open(write_to, 'w')

    # write the document header
    write_lines(newSource, lines[:cutLines[0]])

    # write the import statements
    currentTypeName = ''
    # make sure we iterate through groups in order
    for key, stm in sorted(groups.items(), key=sort_groups):
        if headers:
            typeName = module_type_names[key[0]]
            # commented header for import group
            if currentTypeName != typeName:
                write_line(newSource, '\n# %s libs' % typeName)
                currentTypeName = typeName

        # write the actual statements (sorting each group)
        # TODO: explicit sort here fro greater flexibility
        # key = lambda s: (s.is_from, len(s.statement))   # aesthetic
        # key = lambda s: (s.is_from, s.statement)        # alphabetic
        lineList = sorted(stm)  # separate groups by newline
        write_lines(newSource, lineList)

    # finally rebuild the remaining source code, omitting the previously
    # extracted import lines
    for i, line in enumerate(lines):
        if (i >= cutLines[0]) and (i not in cutLines):
            write_line(newSource, line)

    # closing
    newSource.close()

    # FIXME return str instead of closed StringIO / FileIO object
    return newSource


class ImportStatement(object):
    """
    Helper class for editing and sorting import statements. Treat all types
    of import syntax in the same object so we can switch between styles and
    remove unused statements while still formatting correctly.
    """

    # _sort_by_length = False

    def __init__(self, statement, module, line_nr, names, as_names=()):
        # split the import statement into modules, submodules, names, as_names
        self.statement = str(statement)
        self.module, *self.submodules = str(module).split('.')
        self.line_nr = int(line_nr)
        self.is_from = self.statement.startswith('from')
        self.names = tuple(names)
        self.as_names = tuple(as_names)

    def __repr__(self):
        return repr(self.statement)

    def __str__(self):
        # TODO: write here!!
        return self.statement

    def __lt__(self, other):
        return (self.is_from, len(self.statement)) < \
               (other.is_from, len(other.statement))

        #
        # if self._sort_by_length:
        #     return (self.is_from, len(self.statement)) < \
        #            (other.is_from, len(other.statement))
        # return (self.is_from, self.module) < (other.is_from, other.module)


# class ImportStatement2(object):
#     """
#     Helper class for editing and sorting import statements. Treat all types
#     of import syntax in the same object so we can switch between styles and
#     remove unused statements while still formatting correctly.
#     """
#
#     # _sort_by_length = False
#
#     def __init__(self, node):
#         # split the import statement into modules, submodules, names, as_names
#         if isinstance(ast.Import):
#
#
#
#         self.statement = str(statement)
#         self.module, *self.submodules = str(module).split('.')
#         self.line_nr = int(line_nr)
#         self.is_from = self.statement.startswith('from')
#         self.names = tuple(names)
#         self.as_names = tuple(as_names)


def rewrite(node):
    """rewrite an import node as str"""
    s = ''
    if isinstance(node, ast.ImportFrom):
        # for module relative imports, `node.module` holds the sub-module
        relative = '.' * node.level
        module = ''.join((relative, node.module or '')).strip()
        s = 'from %s ' % module

    # write the aliases
    s += 'import '
    s += ', '.join(' as '.join(filter(None, (alias.name, alias.asname)))
                   for alias in node.names)
    return s

# TODO:


class ImportCapture(ast.NodeVisitor):
    def __init__(self):
        self.statements = []
        self.used_names = []

    def visit_Import(self, node):
        self.statements.append(node)

    def visit_ImportFrom(self, node):
        self.statements.append(node)

    def visit_Name(self, node):
        self.used_names.append(node.id)

    def get_names(self):
        # get imported names as they would reflect in the namespace


class ImportFinder(ast.NodeVisitor):
    """
    Extract, re-construct and buffer import statements from parsed python source
    code.
    """

    # TODO: option for capturing module names...

    def __init__(self, up_to_line=math.inf):
        # collect source code line numbers for *start* of import statements
        self.last_line = float(up_to_line)
        self.line_nrs_1 = []
        self.line_nrs_0 = []
        self.future = []
        self.nr_alias = 1
        self.current_nr = 1

    def visit_Import(self, node):
        self.current_nr = 1
        self.nr_alias = 1

        ln = node.lineno
        if ln <= self.last_line:
            self.line_nrs_1.append(ln)
            self.line_nrs_0.append(ln - 1)
            self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.nr_alias = len(node.names)
        self.current_nr = 1

        ln = node.lineno
        if node.module == '__future__':
            self.future.append(ln)

        if ln <= self.last_line:
            self.line_nrs_1.append(ln)
            self.line_nrs_0.append(ln - 1)
            self.generic_visit(node)


class ImportExtractor(ast.NodeVisitor):
    """
    Extract, re-construct and buffer import statements from parsed python source
    code.
    """

    # TODO: detect if imported things are being used

    def __init__(self, max_line_nr=math.inf, capture_local=True):
        """

        Parameters
        ----------
        max_line_nr: int
            last line of source code for which imports statements will be
            extracted
        local:  bool
            controls whether import statements with local scope will be
            extracted
        """
        # source code line numbers for *start* of import statement. in
        # general not possible to know if end of statement is on next line.
        self.handle_import = True  # controls how module name is captured
        self.current_module = None
        self.statement = ''  # statement buffer
        self.statements = []  # capture import statement on a single line
        self.names = []  # imported names
        self._names_buffer = []
        self.used_names = []  # used to check if imported gets used
        self.line_nrs_0 = []  # zero base line numbers
        self.nr_alias = 1
        self.current_nr = 1
        self.max_line_nr = max_line_nr
        self.capture_local = bool(capture_local)
        self.skip = False

    def visit_Import(self, node):
        # "import bar" or "import foo.bar" style

        # exit if beyond maximum line nr
        line_nr = node.lineno - 1
        if line_nr > self.max_line_nr:
            return

        # optionally capture local imports
        self.skip = (not self.capture_local) and (node.col_offset > 0)
        if self.skip:
            self.generic_visit(node)  # goes to `visit_alias`
            return

        self.handle_import = True
        self.statement = ''
        self._names_buffer = []
        self.current_nr = 1
        self.nr_alias = len(node.names)
        self.line_nrs_0.append(line_nr)
        self.generic_visit(node)  # goes to `visit_alias`

    def visit_ImportFrom(self, node):
        # 'from foo import bar' or 'from ..foo.bar import bla' style

        # exit if beyond maximum line nr
        line_nr = node.lineno - 1
        if line_nr > self.max_line_nr:
            return

        # optionally capture local imports
        self.skip = (not self.capture_local) and (node.col_offset > 0)
        if self.skip:
            self.generic_visit(node)  # goes to `visit_alias`
            return

        # for module relative imports, `node.module` holds the sub-module
        relative = '.' * node.level
        module = ''.join((relative, node.module or '')).strip()

        self.current_module = module
        self.statement = 'from %s import ' % module
        self._names_buffer = []
        self.current_nr = 1
        self.nr_alias = len(node.names)
        self.line_nrs_0.append(line_nr)
        self.handle_import = False
        self.generic_visit(node)  # goes to `visit_alias`

    def visit_alias(self, node):
        if self.skip:
            return

        if self.handle_import:
            # case `visit_Import`
            module = node.name
            statement = 'import %s' % module
            # this will split "import os, re" style imports into 2 lines
            if node.asname:
                statement += (' as %s' % node.asname)
                names = node.asname,
            else:
                names = module,

            # capture statement
            s = ImportStatement(statement, module, self.line_nrs_0[-1], names)
            # line nr captured in `visit_Import` above
            self.statements.append(s)

        else:
            # case `visit_ImportFrom`
            self.statement += node.name
            if node.asname:
                self.statement += (' as %s' % node.asname)
                self._names_buffer.append(node.asname)
            else:
                self._names_buffer.append(node.name)

            last = (self.current_nr == self.nr_alias)
            if not last:
                self.statement += ', '
            else:
                # capture statement
                s = ImportStatement(self.statement, self.current_module,
                                    self.line_nrs_0[-1], self._names_buffer)
                self.statements.append(s)
                # line nr captured in `visit_Import` above
                self.statement = ''

        self.current_nr += 1

    def visit_Name(self, node):
        self.used_names.append(node.id)

    def get_unused_names(self):
        unused = set(self.names)
        for name in self.used_names:
            unused.remove(name)
        return unused

    def get_unused_modules(self):
        unused = []
        for i, s in enumerate(self.statements):
            for name in s.names:
                if name not in self.used_names:
                    unused.append((i, name))
        return unused

    def get_used_statements(self):
        """
        Re-create the
        Returns
        -------

        """
        used = []
        for i, s in enumerate(self.statements):
            keep_names = []
            for name in s.names:
                if name in self.used_names:
                    keep_names.append(name)
            n = len(keep_names)
            if n:
                if n != len(s.names):
                    # s.module, s.line_nr, keep_names
                    # ImportStatement()
                else:
                    used.append(s)
        return used

    def get_modules(self, grouped=True):

        if grouped:
            names = defaultdict(set)
            for s in self.statements:
                name = s.module
                kind = get_module_kind(name)
                names[kind].add(name)
            return names
        else:
            return set(s.module for s in self.statements)
