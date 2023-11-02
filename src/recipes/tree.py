

# std
import re
import math
import numbers
import itertools as itt
from pathlib import Path
from collections import abc

# third-party
import anytree
from anytree.render import _is_last

# relative
from . import op
from .string import strings
from .functionals import always
from .oo.temp import temporarily


# ---------------------------------------------------------------------------- #
# for style in AbstractStyle.__subclasses__():
#     style().end[0]
RGX_TREE_PARSER = re.compile('([│├└ ])[─ ]{2} ')


def _reindent(string, height):
    # regex HACK
    first, *lines = string.splitlines()
    yield first + '\n'
    indents = [len(first) - 1] + [0] * height
    for row in lines:
        matches = [*RGX_TREE_PARSER.finditer(row)]
        if depth := len(matches):
            end = matches[-1].end()
            indents[depth] = len(row) - end - 1
            for m, i in zip(matches, indents):
                yield ' ' * i + m[1]
            yield row[end:]  # + '┐'
        else:
            yield row
        yield '\n'


# ---------------------------------------------------------------------------- #

def _recurse(func, mapping, arg):

    for key, item in mapping.items():
        if isinstance(item, abc.MutableMapping):
            _recurse(func, item, arg)
        else:
            mapping[key] = func(item, arg)

    return mapping

# ---------------------------------------------------------------------------- #


class DynamicIndentRender(anytree.RenderTree):

    def __init__(self, node, style=anytree.ContRoundStyle(), childiter=list,
                 maxlevel=None, attr='name'):

        super().__init__(node, style, childiter, maxlevel)

        self.attr = str(attr)
        self.widths = [0] * (node.height + 1)
        # self.widths[0] = len(getattr(node, self.attr))
        # Adapt the style
        # Use first character of vertical/branch/end strings eg "│", "├", "└"
        style = self.style
        self.style = anytree.AbstractStyle(
            *next(zip(style.vertical, style.cont, style.end)))

    def __iter__(self):
        return self.__next(self.node, ())

    def __next(self, node, continues, level=0):
        name = str(getattr(node, self.attr))
        self.widths[level:] = [len(name), *([0] * (node.height + 1))]
        # print(f'{node.name = :<15} {level = :<10} {self.widths = !s:<20} {continues = !s:<20}')

        yield self.__item(node, continues, self.style, level)

        level += 1
        children = node.children
        if children and (self.maxlevel is None or level < self.maxlevel):
            for child, is_last in _is_last(self.childiter(children)):
                yield from self.__next(child, continues + (not is_last, ), level=level)

    def __item(self, node, continues, style, level):

        if not continues:
            return anytree.render.Row(u'', u'', node)

        selection = (style.empty, style.vertical)
        *items, last = [f'{selection[c]: <{w}}'
                        for w, c in zip(self.widths[1:], continues)]

        branches = f'{(style.end, style.cont)[continues[-1]]: <{self.widths[level + 1]}}'
        indent = ''.join(items)
        # print(f'{items = }\n{last = }\n{branches = }')

        return anytree.render.Row(indent + branches,
                                  indent + last,
                                  node)

    def by_attr(self, attrname='name'):
        with temporarily(self, attr=attrname):
            return super().by_attr(attrname)

# ---------------------------------------------------------------------------- #


class PrettyNode(anytree.Node):

    # rendering option
    renderer = DynamicIndentRender
    renderer_kws = {}

    def __repr__(self):
        # we need this because anytree uses repr when render the tree. Not ideal
        # since it obscures the true object.
        return str(self.name)

    def render(self, **kws):
        """
        A re-spaced rendering of the tree where spacing between levels are set
        dynamically based on the length of the string representation of the
        parents.

        For example:
            └20
              ├13061
              │    ├6.003
              │    │    ├0
              │    │    └1
              │    ├7.003
              │    │    ├0
              │    │    └1
              │    └8.003
              │         ├0
              │         └1
              └2130615.003
                         ├0
                         ├1
                         └2
        """
        return str(self.renderer(self, **{**self.renderer_kws, **kws}))

    def pprint(self):
        print(self.render())


# ---------------------------------------------------------------------------- #


class TreeBuilder:
    """
    Various tree constructors / contractors.
    """

    _get_name = op.itemgetter(0)
    """This function decides the names of the nodes during construction. It will
    be called on each item in the input list at each level, returning the name 
    of that node."""

    _join_names = ''.join
    """This function joins node names together when collapsing the unary
    branches of the tree."""

    @classmethod
    def _build(cls, method_name, *args, root='', collapse=False, **kws):
        """
        Build a tree.  First create the root node with name `root`. Then
        recursively build the tree by calling constructor method with to create
        each branch.

        Parameters
        ----------
        method_name : string
            Name of the method that will graft branches onto nodes.
        root : str, optional
            Name of the root node, by default ''.
        collapse : bool, optional
            Whether to collapse unary branches of the tree after creating it, by
            default False.

        Returns
        -------
        TreeBuilder (or subclass) instance.
            Root node of the tree.
        """

        root = cls(root)
        getattr(root, method_name)(*args, **kws)

        if collapse:
            root.collapse_unary()

        return root

    # def _recurse()

    @classmethod
    def from_strings(cls, items, collapse=True):
        """
        Create the tree from a list of input strings.
        """
        return cls.from_list(strings(items), collapse)

    @classmethod
    def from_list(cls, items, root='', labeller=None, filtering=None, collapse=True):
        """
        Create the tree from a list of input sequences.

        Parameters
        ----------
        items : list
            _description_

        Examples 
        --------
        >>> fonts = Node.from_list(['Domitian-Bold.otf',
        ...                         'Domitian-BoldItalic.otf',
        ...                         'Domitian-Italic.otf',
        ...                         'Domitian-Roman.otf',
        ...                         'EBGaramond-Bold.otf',
        ...                         'EBGaramond-BoldItalic.otf',
        ...                         'EBGaramond-ExtraBold.otf',
        ...                         'EBGaramond-ExtraBoldItalic.otf',
        ...                         'EBGaramond-Initials.otf',
        ...                         'EBGaramond-Italic.otf',
        ...                         'EBGaramond-Medium.otf',
        ...                         'EBGaramond-MediumItalic.otf',
        ...                         'EBGaramond-Regular.otf',
        ...                         'EBGaramond-SemiBold.otf',
        ...                         'EBGaramond-SemiBoldItalic.otf'])
        ... fonts.collapse(max_depth=2)
        ... fonts.pprint()

        ├Domitian-
        │        ├Italic.otf
        │        ├Roman.otf
        │        ├Bold.otf
        │        └BoldItalic.otf
        └EBGaramond-
                   ├Regular.otf
                   ├Bold.otf
                   ├BoldItalic.otf
                   ├ExtraBold.otf
                   ├ExtraBoldItalic.otf
                   ├Initials.otf
                   ├Italic.otf
                   ├Medium.otf
                   ├MediumItalic.otf
                   ├SemiBold.otf
                   └SemiBoldItalic.otf

        Returns
        -------
        Node
            The root node of the tree.
        """

        # build the tree
        return cls._build('_from_list', sorted(items), labeller, filtering,
                          root=root, collapse=collapse)

    def _from_list(self, items, labeller=None, filtering=None):
        """
        Build the tree by grouping items and recursing on sub-groups
        """

        if filtering is not False:
            items = filter(filtering, items)

        for name, items in itt.groupby(items, labeller or self._get_name):
            if name is None:
                continue

            # print(f'{name = }')
            child = type(self)(name, parent=self)
            child._from_list(self._get_children(items), labeller, filtering)

    def _get_children(self, items):
        itr = itt.zip_longest(*items)
        next(itr)  # step down a level
        return zip(*itr)

    # ------------------------------------------------------------------------ #
    @classmethod
    def from_dict(cls, mapping, root='', collapse=False):
        """
        Create the tree from a mapping of input name-value pairs. Values may 
        themselves be mappings.

        Parameters
        ----------
        items : mapping
            _description_

        Examples 
        --------


        Returns
        -------
        Node
            The root node of the tree.
        """

        # build the tree
        return cls._build('_from_dict', mapping,
                          root=root, collapse=collapse)

    def _from_dict(self, mapping):

        cls = type(self)
        for name, items in mapping.items():
            if isinstance(items, abc.MutableMapping):
                child = cls(name, parent=self)
                child._from_dict(items)
            else:
                child = cls(name, parent=self)

        return self

    # ------------------------------------------------------------------------ #
    @property
    def sibling_leaves(self):
        return tuple(child for child in self.siblings if child.is_leaf)

    @property
    def sibling_leaves(self):
        return tuple(child for child in self.siblings if child.is_leaf)

    # ------------------------------------------------------------------------ #
    def collapse(self, max_depth=math.inf, top_down=None, bottom_up=True):
        """
        Collapse the nodes that are deeper than `max_depth`. Each child node
        that is too deep becomes a new sibling node with `name` attribute
        concatenated from parent and child's `name`. 

        Parameters
        ----------
        max_depth : int, optional
            Maximal depth of resulting tree, by default math.inf, which leaves
            the tree unchanged.

        Examples
        --------
        >>> fonts = Node.from_list(['Domitian-Bold.otf',
        ...                         'Domitian-BoldItalic.otf',
        ...                         'Domitian-Italic.otf',
        ...                         'Domitian-Roman.otf',
        ...                         'EBGaramond-Bold.otf',
        ...                         'EBGaramond-BoldItalic.otf',
        ...                         'EBGaramond-ExtraBold.otf',
        ...                         'EBGaramond-ExtraBoldItalic.otf',
        ...                         'EBGaramond-Initials.otf',
        ...                         'EBGaramond-Italic.otf',
        ...                         'EBGaramond-Medium.otf',
        ...                         'EBGaramond-MediumItalic.otf',
        ...                         'EBGaramond-Regular.otf',
        ...                         'EBGaramond-SemiBold.otf',
        ...                         'EBGaramond-SemiBoldItalic.otf'])
        ... fonts.pprint()

        ├Domitian-
        │        ├Bold
        │        │   ├.otf
        │        │   └Italic.otf
        │        ├Italic.otf
        │        └Roman.otf
        └EBGaramond-
                   ├Bold
                   │   ├.otf
                   │   └Italic.otf
                   ├ExtraBold
                   │        ├.otf
                   │        └Italic.otf
                   ├I
                   │├nitials.otf
                   │└talic.otf
                   ├Medium
                   │     ├.otf
                   │     └Italic.otf
                   ├Regular.otf
                   └SemiBold
                           ├.otf
                           └Italic.otf

        >>> fonts.collapse(max_depth=2)
        >>> fonts.pprint()

        ├Domitian-
        │        ├Italic.otf
        │        ├Roman.otf
        │        ├Bold.otf
        │        └BoldItalic.otf
        └EBGaramond-
                   ├Regular.otf
                   ├Bold.otf
                   ├BoldItalic.otf
                   ├ExtraBold.otf
                   ├ExtraBoldItalic.otf
                   ├Initials.otf
                   ├Italic.otf
                   ├Medium.otf
                   ├MediumItalic.otf
                   ├SemiBold.otf
                   └SemiBoldItalic.otf

        Note that, in this example, the root node's `name` attribute is
        just an empty string '', which formats as a newline in string
        representation above.


        Returns
        -------
        changed: bool
            Whether the tree was altered or not.
        """
        if max_depth == -1:
            max_depth = math.inf

        if not isinstance(max_depth, numbers.Integral) or max_depth < 1:
            msg = '`max_depth` parameter should be a positive integer.'
            if max_depth == 0:
                msg += ('Use `list(node.descendants)` to get a fully collapsed '
                        'list of nodes.')
            raise ValueError(msg)

        changed = False
        top_down = ~bottom_up if (top_down is None) else top_down
        collapse = self.collapse_top_down if top_down else self.collapse_bottom_up
        while True:
            changed = collapse(max_depth)
            if not changed:
                break

        return changed

    def collapse_top_down(self, max_depth):
        changed = self.collapse_unary() if self.is_root else False
        # root node is always at 0, so first items at depth 1, hence > not >=
        if self.is_leaf and (self.depth > max_depth):
            # reparent this child to the grand parent if it's a leaf node, and
            # concatenate the names
            self.grandparent_adopts()

            # self.parent.collapse(max_depth)
            changed = True

        # edit remaining children
        for child in self.children:
            changed |= child.collapse(max_depth)

        # logger.debug('{}: depth={}, changed {}', self.name, self.depth, changed)
        # logger.debug('\n{}', self.root.render())

        return changed

    def collapse_bottom_up(self, max_depth=math.inf):

        # if self.depth > max_depth:

        # changed = False
        # if self.is_leaf:
        #     return False
        if self.depth <= max_depth:
            return False

        leaves = set(self.leaves)
        while leaves:
            # pick a starting leaf
            leaf = leaves.pop()
            siblings = set(leaf.parent.children)
            # all these leaves can be re-parented
            leaves -= siblings
            # get siblings that are also leaf nodes
            sibling_leaves = set(self.sibling_leaves)
            # sibling_leaves = siblings.intersection(leaves) - {self}
            # if len(sibling_leaves) < 2:
            #     continue

            # reparent this child to the grand parent and concatenate the names
            for leaf in sibling_leaves:
                leaf.grandparent_adopts()

            changed = True

        return changed

    def grandparent_adopts(self):
        # re-parent this child to the grand parent and concatenate the names
        parent = self.parent
        self.name = parent.name + self.name
        self.parent = parent.parent

        # check if parent became a leaf node
        if parent.is_leaf:
            # orphan this leaf, since it is now redundant
            self.parent.children = parent.siblings

    def collapse_unary(self):
        """
        Collapse all unary branches of the node ie. If a node has only one child 
        (branching factor 1), attach the grand child to the parent node and 
        discard / orphan the child node.

        For example:
            └── 2
                └── 0
                    └── 1
                        └── 3
                            └── 0
                                └── 6
                                    └── 1
                                        ├── 6
                                        │   └── .
                                        │       └── 0
                                        │           └── 0
                                        │               └── 3
                                        │                   ├── 0
                                        │                   └── 1
                                        ├── 7
                                        │   └── .
                                        │       └── 0
                                        │           └── 0
                                        │               └── 3
                                        │                   ├── 0
                                        │                   └── 1
                                        └── 8
                                            └── .
                                                └── 0
                                                    └── 0
                                                        └── 3
                                                            ├── 0
                                                            └── 1

        Becomes:
            └── 20
                └── 13061
                    ├── 6.003
                    │   ├── 0
                    │   └── 1
                    ├── 7.003
                    │   ├── 0
                    │   └── 1
                    └── 8.003
                        ├── 0
                        └── 1

        """
        child = self
        changed = False
        while len(child.children) == 1:
            child, = child.children
            self.name = self._join_names((self.name, child.name))
            changed = True
        self.children = child.children

        for child in self.children:
            changed |= child.collapse_unary()

        return changed



class Node(PrettyNode, TreeBuilder):

    def __getitem__(self, key):
        if self.is_leaf:
            raise ValueError('Node has no children.')

        if isinstance(key, numbers.Integral):
            return self.children[key]

        for child in self.children:
            if key == child.name:
                return child

        raise KeyError(f'Could not get child node for index key {key!r}.')

    def as_dict(self, attr='name', leaf_attr='name'):
        if self.is_leaf:
            return getattr(self, leaf_attr)

        return {getattr(child, attr): child.as_dict(attr, leaf_attr)
                for child in self.children}
    
    # def __contains__(self, key):
    #     return next((c for c in self.children if c.name == key), None) is not None

    # def append(self, name):
    #     child = type(self)(name)
    #     child.parent = self.parent


# ---------------------------------------------------------------------------- #
def _sort_key(node):
    return (node.as_path().is_dir(), node.name)


def _pprint_sort(children):
    return sorted(children, key=_sort_key)


def _ignore_names(ignore):

    if isinstance(ignore, str):
        ignore = [ignore]

    if not (ignore := list(ignore)):
        return always(True)

    def wrapper(path):
        return (path.name not in ignore)

    return wrapper


class FileSystemNode(Node):

    # pprinting
    renderer_kws = dict(childiter=_pprint_sort)

    @classmethod
    def from_path(cls, folder, collapse=True, ignore=()):

        folder = Path(folder)
        assert folder.exists()

        return cls._build('_from_list',
                          folder.iterdir(), None, _ignore_names(ignore),
                          root=str(folder), collapse=collapse)

    @staticmethod
    def _get_name(path):
        return f'{path.name}{"/" * path.is_dir()}'

    @staticmethod
    def _get_children(paths):
        path = next(paths)
        if path.is_dir():
            yield from path.iterdir()

    def as_path(self):
        """The node as a pathlib.Path object."""
        path = Path()
        for _ in (*self.ancestors, self):
            path /= str(_)

        return path
