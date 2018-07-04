import math
import os
import re

import textwrap
from collections import defaultdict

from IPython import embed

SRE_SPACE = re.compile('(\s*)')
SRE_LINE_COMMENT = re.compile('((\s*)#)(.*)')  # (\s*#)(\s*?)(.*)


def tidy(filename, up_to_line=math.inf, hard_wrap=80, inline_shift=0,
         remove_commented_source=True, remove_todo=True, remove_fixme=True, ):
    """

    Parameters
    ----------
    filename: str, pathlib.Path
        system path pointing to the '*.py' file
    up_to_line: int
        only lines up to (and including) this line will be edited
    hard_wrap: int
        line wdth at which comments will be hard wrapped
    inline_shift: int
        move long inline comments one line up or down
    remove_commented_source:
        remove source code that has been commented out
    remove_todo: bool
        filter TODO comments
    remove_fixme: bool
        filter FIXME comments


    Returns
    -------

    """
    filename = str(filename)
    with open(filename) as fp:
        source = fp.read()

    lines = source.splitlines()

    comments, blocks = extract(lines, up_to_line)
    return comments, blocks

    if remove_commented_source:
        # try to parse the code block
        pass


    # map source line indices to slices
    block_slices = list(map(slice, *zip(*blocks)))

    # slices can be used to get comment blocks from list of source lines
    for sl in block_slices:
        block = lines[sl]
        if max(map(len, block)) > hard_wrap:
            match = SRE_LINE_COMMENT.match(block[0])
            repl, indent, content = match.groups()

            print(repr(indent))

            block_txt = os.linesep.join(block)
            block_txt = block_txt.replace(repl, '')
            block_txt = textwrap.wrap(block_txt, hard_wrap,
                                      initial_indent=indent,
                                      subsequent_indent=indent)

            print('-' * 80)
            print(os.linesep.join(block_txt))
            print('-' * 80)

    # initial_indent
    return blocks


def extract(lines, up_to_line=math.inf):
    """
    extract comments from source code lines

    """
    # first find the comments
    # comments = {}
    comments = []       # comments with 
    line_nrs = []
    in_line = []        # boolean flags indicating if comment preceded by code
    blocks = []         # multi-line blocks start and end numbers
    prev = -2
    in_block_prev = False
    blk0, blk1 = 0, None
    for i, line in enumerate(lines):
        if '#' in line:
            preceding, content = line.split('#', 1)

            # check if inline
            inline = not ((preceding == '') or preceding.isspace())

            # check if part of a comment block
            in_block_current = (not inline) and (i == prev + 1)
            # get start / end lines for block
            if in_block_current:
                if in_block_prev:
                    # same block
                    blk1 = i
            else:
                # new block
                if blk1:
                    blocks.append([blk0, blk1 + 1])
                blk0, blk1 = i, None

            # capture
            # comments[i] = (content, inline)

            in_block_prev = not inline
            prev = i

        if i > up_to_line:
            break

    return comments, blocks

# def hard_wrap(filename, width=80, up_to_line=math.inf, ):
#

# remove_todo, remove_fixme, remove_commented_code
