"""
Emulate bash brace expansion
"""


# std
import re
import math

# relative
from .. import op
from ..tree.node import Node
from ..functionals import negate
from ..containers import split_where
from ..string import delimited, shared_affix, strings


RGX_CURLY_BRACES = re.compile(r'(.*?)\{([^}]+)\}(.*)')
RGX_BASH_RANGE = re.compile(r'(\d+)[.]{2}(\d+)')

braces = delimited.Parser('{}')

# ---------------------------------------------------------------------------- #
# utility functions


def ints(items):
    return [*map(int, items)]


def unclosed(string, open_, close):
    return string.count(open_) - string.count(close)

# brace expansion
# ---------------------------------------------------------------------------- #

# class BraceExpression:
#     def expand
#     def contract


def brace_expand_iter(string, level=0):

    # handle special bash expansion syntax here  xx{12..15}.fits
    match = braces.match(string)
    if match is None:
        yield string
        return

    head, tail = string[:match.start], string[match.end + 1:]
    # print(f'{inside=}, {head=}, {tail=}')
    for new in _expander(match.enclosed, head, tail):
        yield from brace_expand_iter(new, level=level+1)


def _expander(item, head='', tail=''):
    rng = RGX_BASH_RANGE.fullmatch(item)
    # bash expansion syntax implies an inclusive number interval
    items = range(int(rng[1]), int(rng[2]) + 1) if rng else delimited.csplit(item)
    for x in items:
        yield f'{head}{x}{tail}'


def brace_expand(pattern):
    # >>> brace_expand('root/{search,these}/*.tex')
    # ['root/search/*.tex', 'root/these/*.tex']
    # >>> brace_expand('/**/*.{png,jpg}')
    # ['/**/*.png', '/**/*.jpg']

    return list(brace_expand_iter(str(pattern)))


# ---------------------------------------------------------------------------- #
# Brace Contraction

def is_unary(node):
    """check whether a node has only one child"""
    while len(node.children) == 1:
        node, = node.children
    return not bool(node.children)


def get_tree(items, depth=-1):
    # NOTE that the depth parameter here does not refer to the depth of the
    # returned tree, but rather the depth of brace nesting
    # collapse the tree
    return BraceExpressionNode.from_list(items).collapse(depth)


class BraceExpressionNode(Node):  # pylint: disable=function-redefined
    """Node representing a branching point in the brace expression."""

    def get_names(self, s=''):
        if self.is_leaf:
            yield s + self.name
            return

        for child in self.children:
            yield from child.get_names(s + self.name)

    def to_list(self):
        return list(self.get_names())

    def collapse_leaves(self, max_nest=math.inf):
        """
        Merge nodes that are all leaves of the same parent.

        For example
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

        Becomes:
            └── 20
                └── 13061
                    ├── 6.003
                    │   └── {0,1}
                    ├── 7.003
                    │   └── {0,1}
                    └── 8.003
                        └── {0,1}

        After running `collapse_unary` on this tree, the result would be:
            2013061
                ├── 6.003{0,1}
                ├── 7.003{0,1}
                └── 8.003{0,1}

        Another run of `collapse_leaves` gives:
            2013061
                └── {6,7,8}.003{0,1}

        """
        changed = False
        if self.is_leaf:
            return changed

        leaves = set(self.leaves)
        while leaves:
            leaf = leaves.pop()
            siblings = set(leaf.parent.children)
            leaves -= siblings
            # get siblings that are also leaf nodes
            sibling_leaves = set(self.sibling_leaves)
            # sibling_leaves = siblings.intersection(leaves)
            if len(sibling_leaves) < 2:
                continue

            nested = max(map(braces.depth, strings(sibling_leaves)))
            if nested >= max_nest:
                continue

            leaf.name = contract(sorted(map(str, sibling_leaves)))
            leaf.parent.children = (leaf, *(siblings - sibling_leaves - {leaf}))
            changed = True

        return changed

    def collapse(self, max_nest=-1):
        """
        Collapse the tree down to required level.

        Parameters
        ----------
        max_nest : int, optional
            [description], by default -1

        Examples
        --------
        >>> 

        Returns
        -------
        bash.Node
            [description]
        """
        # collapse the tree
        self.collapse_unary()
        # Fully contracted expressions can often be too complicated to easily
        # parse mentally if they are very deep. We therefore allow limiting the
        # depth.
        # oheight = self.height
        max_nest = math.inf if max_nest in (-1, math.inf) else int(max_nest)
        if max_nest == 0:
            return self

        changed = False
        while self.height:
            changed = (self.collapse_unary() | self.collapse_leaves(max_nest))
            if not changed:
                break

        return self


def contract(items):
    """
    Perform a single contraction a sequence of strings.

    Parameters
    ----------
    items : sequence of str
        Sequence of strings to be represented compactly as brace expression.


    Examples
    --------
    >>> contract([9, 10, 11, 12])
    '{09..12}'
    >>> contract([*'12345'])
    '{1..5}'
    >>> contract([1,5,7])
    '{1,5,7}'
    >>> contract(['whimsical', 'whims'])
    'whims{,ical}'


    Returns
    -------
    str
        Brace expression à la bash.

    """
    # convert to strings
    items = strings(items)

    if not items:
        raise ValueError('Cannot contract and empty sequence.')

    # find prefixes / suffixes
    head, tail = shared_affix(items)
    # make sure we keep preexisting brace expressions intact
    head = head.rstrip('{')
    tail = tail.lstrip('}')
    i0, i1 = (len(head), -len(tail) or None)
    middle = [item[i0:i1] for item in items]

    try:
        nrs = sorted(ints(middle))
    except ValueError:  # as err
        # not a numeric sequence.
        pass
    else:
        # we have a number sequence! Split sequence into contiguous parts.
        # split where pointwise difference greater than 1.
        middle = []
        enum = iter(nrs)
        for nrs in split_where(nrs, (lambda x, _: x - next(enum) > 1), start=1):
            if len(nrs) > 2:
                middle.append(contract_range(nrs))
            else:
                middle.extend(map(str, nrs))

    brace = '{}' if len(middle) > 1 else ('', '')
    middle = ",".join(middle).join(brace)
    return ''.join((head, middle, tail))


def contract_range(seq):
    """
    Contract a sequence of consecutive integers 
        [9, 10, 11, 12]  --> '{09..12}'
    """

    first, *rest = seq
    if not rest:
        return str(first)

    # zfill first, embrace: eg: {09..12}
    *middle, last = rest
    sep = '..' if middle else ','
    first, last = str(first), str(last)
    # brace = '{}' if brackets > 1 else ('', '')
    return f'{{{first:>0{len(last)}}{sep}{last}}}'  # .join(brace)


# @ doc.splice(contract, 'examples', 'Parameters[items]')
def brace_contract(items, depth=-1):
    """
    Brace contract a sequence of strings. Return a brace expression à la bash.

    Parameters
    ----------
    depth : int
        Control the maximal depth of contracted expressions. Fully contracted
        expressions can often be too complicated to easily parse mentally if
        they are very deep. We therefore allow limiting the maximal level of
        nesting by specifying a positive integer *depth*. By default, (depth=-1)
        the expression will be fully contracted.

    Returns
    -------
    list
        For depth == -1, the list will have unit length (full contraction). In
        general, for depth != -1 the list may contain more than 1 item if the
        input list contains more than one item.
    """
    # special cases
    if isinstance(items, str):
        items = [items]

    n = len(items)
    if n == 0:
        raise ValueError('Cannot contract and empty sequence.')

    if n == 1:
        # simply remove single items enclosed in delimited. NOTE this behaviour
        # is different from what bash does: it simply uses the name containing
        # {x} elements verbatim, which we don't want in this context.
        return braces.remove(items[0],
                             condition=negate(op.contained(',').within))

    #
    if depth == 1:
        return contract(items)

    #
    tree = get_tree(items, depth)
    if tree.height:
        return tree.to_list()

    # sometimes single contraction is to be prefered: for example for
    # filenames that have a numeric sequence
    once = contract(items)
    if len(tree.name) > len(once):
        return once
    return tree.name
