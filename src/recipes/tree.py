

# std
import re
import math
import numbers
import itertools as itt
from pathlib import Path
from typing import MutableMapping

# third-party
import anytree
from anytree.render import _is_last
from loguru import logger

# relative
from . import op
from .string import strings
from .oo.temp import temporarily
from .decorators import sharedmethod


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


class DynamicIndentRender(anytree.RenderTree):

    def __init__(self, node, style=anytree.ContRoundStyle(), childiter=list, maxlevel=None):
        super().__init__(node, style, childiter, maxlevel)

        self.attr = 'name'
        self.widths = [0] * (node.height + 1)
        # Adapt the style
        # Use first character of vertical/branch/end strings eg "│", "├", "└"
        style = self.style
        self.style = anytree.AbstractStyle(
            *next(zip(style.vertical, style.cont, style.end)))

    def __iter__(self):
        return self.__next(self.node, tuple())

    def __next(self, node, continues, level=0):
        name = str(getattr(node, self.attr))
        self.widths[(level - 1):] = [len(name), *([0] * (node.height + 1))]
        # print(f'next {node=:}, {level=:}, {self.indents=:}, {continues=:}')

        yield self.__item(node, continues, self.style, level)

        children = node.children
        level += 1
        if children and (self.maxlevel is None or level < self.maxlevel):
            children = self.childiter(children)
            for child, is_last in _is_last(children):
                yield from self.__next(child, continues + (not is_last, ), level=level)

    def __item(self, node, continues, style, level):

        if not continues:
            return anytree.render.Row(u'', u'', node)

        selection = (style.empty, style.vertical)
        items = [f'{selection[c]: <{w}}' for w, c in zip(self.widths, continues)]
        branch = f'{(style.cont if continues[-1] else style.end): <{self.widths[level]}}'
        indent = ''.join(items[:-1])
        pre = indent + branch
        fill = ''.join((indent, items[-1]))
        # print(f'item {pre=:}, {fill=:}, {node=:}')
        return anytree.render.Row(pre, fill, node)

    def by_attr(self, attrname='name'):
        with temporarily(self, attr=attrname):
            return super().by_attr(attrname)

# ---------------------------------------------------------------------------- #


class PrintNode(anytree.Node):

    # rendering option
    renderer = DynamicIndentRender

    def render(self):
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
        return str(self.renderer(self))

    def pprint(self):
        print(self.render())

# ---------------------------------------------------------------------------- #


class Node(PrintNode):  # StringNode
    """
    An `anytree.Node` that builds trees based on a list of input strings.
    Can be used to represent file system trees etc.
    """

    get_label = op.itemgetter(0)
    """This function decides the names of the nodes. It will be called on each
    item in the input list at each level, returning the name of that node."""

    join_labels = ''.join
    """This function joins node names together when collapsing the tree"""

    @property
    def sibling_leaves(self):
        return tuple(child for child in self.siblings if child.is_leaf)

    @classmethod
    def from_strings(cls, items, collapse=True):
        """
        Create the tree from a list of input strings.
        """
        return cls.from_list(strings(items))

    @classmethod
    def from_list(cls, items, labeller=None, filtering=None, collapse=True):
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

        root = cls('')
        root._make_branch(sorted(items), labeller, filtering)
        if collapse:
            root.collapse_unary()
        return root

    @sharedmethod
    def _make_branch(self, items, labeller=None, filtering=None):
        """
        Build the tree by grouping a
        grouping when subsequent letters have the same prefix.
        """
        if filtering is not False:
            items = filter(filtering, items)

        cls = type(self)
        if constructor := (cls is type):
            parent = None  # root node
            cls = self
        else:
            parent = self

        for gid, keys in itt.groupby(items, labeller or self.get_label):
            child = cls(gid, parent=parent)
            child._make_branch(self._step_down(keys), labeller, filtering)

        if constructor:
            return child  # this is actually the root node ;)

    def _step_down(self, items):
        itr = itt.zip_longest(*items)
        next(itr)  # step down a level
        return zip(*itr)

    def __repr__(self):
        # we need this because anytree uses repr to render the tree. Not ideal
        # since it obscures the true object.
        return str(self.name)

    def __getitem__(self, key):
        if self.is_leaf:
            raise ValueError('Node has no children.')

        if isinstance(key, numbers.Integral):
            return self.children[key]

        for child in self.children:
            if key == child.name:
                return child

        raise KeyError(f'Could not get child node for index key {key}.')

    # def append(self, name):
    #     child = type(self)(name)
    #     child.parent = self.parent

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
        # reparent this child to the grand parent and concatenate the names
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
            self.name = self.join_labels((self.name, child.name))
            changed = True
        self.children = child.children

        for child in self.children:
            changed |= child.collapse_unary()

        return changed


class FileSystemNode(Node):

    # @classmethod
    # def make(cls, items, labeller=None, filtering=None):

    @classmethod
    def from_path(cls, folder, collapse=True):
        folder = Path(folder)
        assert folder.exists()

        root = cls._make_branch([folder])

        if collapse:
            root.collapse_unary()

        return root

    @staticmethod
    def get_label(path):
        return f'{path.name}{"/" * path.is_dir()}'

    @staticmethod
    def _step_down(paths):
        path = next(paths)
        if path.is_dir():
            yield from path.iterdir()
