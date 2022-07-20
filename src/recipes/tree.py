

# std
import re
import math
import numbers
import itertools as itt
from typing import MutableMapping

# third-party
import anytree
from anytree import AbstractStyle, ContRoundStyle
from anytree.render import RenderTree, Row, _is_last
from loguru import logger

# local
from recipes.oo.temp import temporarily

# relative
from . import op
from .string import remove_prefix, strings


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


# ---------------------------------------------------------------------------- #


class DynamicIndentRender(RenderTree):

    def __init__(self, node, style=ContRoundStyle(), childiter=list, maxlevel=None):
        super().__init__(node, style, childiter, maxlevel)

        self.attr = 'name'
        self.widths = [0] * (node.height + 1)
        # Adapt the style
        # Use first character of vertical/branch/end strings eg "│", "├", "└"
        style = self.style
        self.style = AbstractStyle(*next(zip(style.vertical, style.cont, style.end)))

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
            return Row(u'', u'', node)
        selection = (style.empty, style.vertical)
        items = [f'{selection[c]: <{w}}' for w, c in zip(self.widths, continues)]
        branch = f'{style.cont if continues[-1] else style.end: <{self.widths[level]}}'
        indent = ''.join(items[:-1])
        pre = indent + branch
        fill = ''.join((indent, items[-1]))
        # print(f'item {pre=:}, {fill=:}, {node=:}')
        return Row(pre, fill, node)

    def by_attr(self, attrname='name'):
        with temporarily(self, attr=attrname):
            return super().by_attr(attrname)

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

    get_prefix = op.itemgetter(0)
    """This function decides the names of the nodes. It will be called on each
    string in the input list, returning the name of the of that node parent."""

    @property
    def sibling_leaves(self):
        return tuple(child for child in self.siblings if child.is_leaf)

    @classmethod
    def from_list(cls, items, collapse=True):
        """
        Create the tree from a list of input strings.

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

        # ensure list of strings
        items = sorted(strings(items))

        # build the tree
        root = cls('')
        root.make_branch(items)
        if collapse:
            root.collapse_unary()
        return root

    def make_branch(self, words):
        """
        Build the tree by splitting the list of strings letter by letter and
        grouping when subsequent letters have the same prefix.
        """
        for base, words in itt.groupby(filter(None, words), self.get_prefix):
            child = self.__class__(base, parent=self)
            child.make_branch((remove_prefix(w, base)
                               for w in filter(None, words)))

    def __repr__(self):
        # we need this because anytree uses repr to render the tree. Not ideal
        # since it obscures the true object.
        return str(self.name)

    def __getitem__(self, key):
        if self.children:
            return self.children[key]
        raise ValueError('Node has no children.')

    # def append(self, name):
    #     child = type(self)(name)
    #     self.children = (*self.children, child)

    def collapse(self, max_depth=math.inf):
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

        if self.is_leaf:
            return False

        changed = self.collapse_unary() if self.is_root else False

        if self.depth >= max_depth:
            # leaves become siblings with new names
            for leaf in self.leaves:
                leaf.name = self.name + leaf.name
                leaf.parent = self.parent

            if not self.children:
                self.parent.children = self.siblings

        # edit remaining children
        for child in self.children:
            changed |= child.collapse(max_depth)

        return changed

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
            self.name += child.name
            changed = True
        self.children = child.children

        for child in self.children:
            changed |= child.collapse_unary()

        return changed


class FileSystemNode(Node):

    def get_prefix(self, item):
        return ''.join(item.partition(r'/')[:-1])
