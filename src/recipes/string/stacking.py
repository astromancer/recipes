"""
Horizontal / vertical stacking of strings.
"""


# std
import numbers
import itertools as itt

# third-party
import more_itertools as mit

# relative
from .. import op
from ..iter import where
from ..containers.ensure import duplicate_if_scalar
from .justify import justify


# ---------------------------------------------------------------------------- #

def width(string):
    """
    Find the width of a paragraph by finding the longest line. Works by indexing
    the newline positions and differencing pairs of indices, so all characters
    in the string, including non-display chatacters, are counted.

    Parameters
    ----------
    string : str
        A line or paragraph of text.

    Returns
    -------
    int
        Length of the longest line of text.
    """
    indices = [*where(string, '\n'), len(string)]

    if len(indices) == 1:
        return indices[0]

    return -min(map(op.sub, *zip(*mit.pairwise(indices))))


def _max_line_width(lines):
    return max(map(len, lines))


def hstack(strings, spacing=0, offsets=(), width_func=_max_line_width):
    """
    Stick two or more multi-line strings together horizontally.

    Parameters
    ----------
    strings
    spacing : int
        Number of horizontal spaces to be added as a column between the string
        blocks.
    offsets : Sequence of int
        Vertical offsets in number of rows between string blocks.


    Returns
    -------
    str
        Horizontally stacked string
    """

    # short circuit
    if isinstance(strings, str):
        return strings

    if len(strings) == 1:
        return str(strings[0])

    # get columns and trim trailing whitespace column
    columns = _get_hstack_columns(strings, spacing, offsets, width_func)
    columns = itt.islice(columns, 2 * len(strings) - 1)
    return '\n'.join(map(''.join, zip(*columns)))


def _get_hstack_columns(strings, spacing, offsets, width_func):

    # resolve offsets
    if isinstance(offsets, numbers.Integral):
        offsets = [0] + [offsets] * (len(strings) - 1)

    offsets = list(offsets)
    assert len(offsets) <= len(strings)

    # first we need to compute the widths
    widths = []
    lines_list = []
    max_length = 0
    for string, off in itt.zip_longest(strings, offsets, fillvalue=0):
        lines = str(string).splitlines()
        max_length = max(len(lines), max_length)
        widths.append(width_func(lines))   # ansi.length(lines[0])
        lines_list.append(([''] * off) + lines)

    # Intersperse columns with whitespace
    for lines, width in zip(lines_list, widths):
        # fill whitespace
        yield mit.padded(lines, ' ' * (width), max_length)
        yield itt.repeat(' ' * spacing, max_length)


def vstack(strings,  justify_='<', width_=None, spacing=0):

    s = list(filter(lambda s: s is not None, strings))
    justify_ = duplicate_if_scalar(justify_, len(s))

    if width_ is None:
        width_ = max(map(width, s))

    vspace = '\n'.join(itt.repeat(' ' * width_, spacing))
    itr = itt.zip_longest(s, justify_, fillvalue=justify_)
    itr = (justify(par, just, width_) for par, just in itr)
    return '\n'.join(
        mit.interleave_longest(itr, itt.repeat(vspace, len(s) - 1))
    )
