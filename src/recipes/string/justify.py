"""
Justify (align) and overlay strings.
"""


# std
from warnings import warn

# relative
from ..iter import where

# ---------------------------------------------------------------------------- #
JUSTIFY_MAP = {
    'r': '>',
    'l': '<',
    'c': '^',
    's': ' '
}

# ---------------------------------------------------------------------------- #

def resolve_justify(align):
    align = JUSTIFY_MAP.get(align.lower()[0], align)
    if align not in '<^> ':
        raise ValueError(f'Unrecognised alignment {align!r}')
    return align


def justify(text, align='<', width=None, length_func=len, formatter=str.format):
    """
    Justify a paragraph of text.

    Parameters
    ----------
    text : str
        Text to justify.
    align : str, optional
        Alignment, by default '<'.
    width : int, optional
        Line width. The default is None, which uses the terminal width if
        available, falling back to classic 80.

    Returns
    -------
    str
        Justified text.
    """
    return '\n'.join(_justify(text, align, width, length_func, formatter))


def _justify(text, align, width, length_func, formatter):

    align = resolve_justify(align)
    lines = text.splitlines()
    linewidths = list(map(length_func, lines))
    widest = max(linewidths)
    width = int(width or widest)
    if widest > width:
        warn(f'Requested paragraph width of {width} is less than the '
             f'length of widest line: {widest}.')

    if align != ' ':
        for lw, line in zip(linewidths, lines):
            yield formatter('{: {}{}}', line, align, max(width, lw))
        return

    for w, line in zip(linewidths, lines):
        delta = width - w
        if delta < 0:
            yield line

        indices = list(where(line, ' '))
        d, r = divmod(delta, len(indices))
        for j, k in enumerate(indices[::-1]):
            yield insert(' ' * d + (j < r), line, k)


def overlay(text, background='', align='^', width=None):
    """
    Overlay `text` on `background` using given `alignment`.

    Parameters
    ----------
    text : [type]
        [description]
    background : str, optional
        [description], by default ''
    align : str, optional
        [description], by default '^'
    width : [type], optional
        [description], by default None

    Examples
    --------
    >>> 

    Returns
    -------
    [type]
        [description]

    Raises
    ------
    ValueError
        [description]
    """
    # TODO: drop width arg
    # TODO: verbose alignment name conversions. see motley.table.get_alignment
    # TODO: can you acheive this with some clever use of fstrings?
    # {line!s: {align}{width}}

    if not (background or width):
        # nothing to align on
        return text

    if not background:
        # align on clear background
        background = ' ' * width
    elif not width:
        width = len(background)

    if len(background) < len(text):
        # background will be overwritten. Alignment is pointless.
        return text

    # left aligned
    if align == '<':
        return text + background[len(text):]

    # right aligned
    if align == '>':
        return background[:-len(text)] + text

    # center aligned
    if align == '^':
        div, mod = divmod(len(text), 2)
        pl, ph = div, div + mod
        # start and end indeces of the text in the center of the background
        idx = width // 2 - pl, width // 2 + ph
        # center text on background
        return background[:idx[0]] + text + background[idx[1]:]

    raise ValueError(f'Alignment character {align!r} not understood')


# def centre(self, width, fill=' ' ):

# div, mod = divmod( len(self), 2 )
# if mod: #i.e. odd window length
# pl, ph = div, div+1
# else:  #even window len
# pl = ph = div

# idx = width//2-pl, width//2+ph
# #start and end indeces of the text in the center of the progress indicator
# s = fill*width

# return s[:idx[0]] + self + s[idx[1]:]                #center text
