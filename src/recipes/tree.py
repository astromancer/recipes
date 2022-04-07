

# std
import re
import itertools as itt

# third-party
import anytree

# relative
from . import op
from .string import remove_prefix, strings


class Node(anytree.Node):
    """
    An `anytree.Node` that builds trees based on a list of input strings.
    Can be used to represent file system trees etc.
    """

    # This function decides the names of the nodes. It will be called on each
    # string in the input list, returning the name of the of that node parent
    get_prefix = op.itemgetter(0)

    # rendering option
    use_dynamic_spacing = True

    @classmethod
    def from_list(cls, items):
        # ensure list of strings
        items = sorted(strings(items))

        # build the tree
        root = cls('')
        root.make_branch(items)
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

    def collapse_unary(self):
        """
        Collapse all unary branches of the node ie. If a node has only one child 
        (branching factor 1), attach the grand child to the parent node and 
        orphan the child node.

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
        s = str(anytree.RenderTree(self))

        if not self.use_dynamic_spacing:
            return s

        pre = re.compile('([│├└ ])[─ ]{2} ')
        first, *lines = s.splitlines()
        new = first + '\n'
        indents = [len(first) - 1] + [0] * self.height
        for row in lines:
            matches = [*pre.finditer(row)]
            if depth := len(matches):
                end = matches[-1].end()
                indents[depth] = len(row) - end - 1
                for m, i in zip(matches, indents):
                    new += ' ' * i + m[1]
                new += row[end:]  # + '┐'
            else:
                new += row
            new += '\n'
        return new

    def pprint(self):
        print(self.render())


class FileSystemNode(Node):

    def get_prefix(self, item):
        return ''.join(item.partition(r'/')[:-1])
