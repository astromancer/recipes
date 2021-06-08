import os
import re
import ast
import math
import textwrap

SRE_SPACE = re.compile('(\s*)')
SRE_LINE_COMMENT = re.compile('((\s*)#)(.*)')  # (\s*#)(\s*?)(.*)


# FIXME: have to check that this doesn't flag strings containing a #


def tidy(filename, up_to_line=math.inf, hard_wrap=80, inline_shift=0,
         remove_commented_source=True, remove_todo=True, remove_fixme=True,
         remove_empty=False):
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

    # comments, blocks = extract(lines, up_to_line)
    # return comments, blocks

    line_nrs, comments, inlines, iblocks = extract(lines, up_to_line)
    # return extract(lines, up_to_line)

    remove = set()
    if remove_commented_source:
        for b in iblocks:
            nrs = range(*b)
            s = '\n'.join(comments[l] for l in nrs)
            if is_source(s):
                remove |= set(nrs)

    return remove

    # map source line indices to slices
    # block_slices = list(map(slice, *zip(*blocks)))

    # slices can be used to get comment blocks from list of source lines
    for b in iblocks:
        block = lines[slice(*b)]
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


# def _make_blocks():
#     blocks =
#

def extract(lines, up_to_line=math.inf):
    """
    extract comments from source code lines

    """
    # first find the comments
    comments = {}
    # comments = []       # comments with octothorp / hex / hash stripped
    line_nrs = []  # 0 base line numbers
    inlines = []  # boolean flags indicating if comment preceded by code
    iblock = []  # multi-line blocks start and end numbers
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
                    iblock.append((blk0, blk1 + 1))
                blk0, blk1 = i, None

            # capture
            comments[i] = content  # (content, inline)
            # comments.append(content)
            inlines.append(inline)
            line_nrs.append(i)

            # flags for block id
            in_block_prev = not inline
            prev = i

        # exit clause
        if i > up_to_line:
            break

    return line_nrs, comments, inlines, iblock


def _is_expr(node):
    if isinstance(node, ast.Expr):
        if isinstance(node.value, ast.Name):
            return False


def is_source(block):
    try:
        # try to parse the code block
        tree = ast.parse(textwrap.dedent(block))

        # if we got here, the compiler thinks this is source code.
        # Note this check will flag the following block (between ---) as valid
        # source code even though it is not:
        # -------------------------------------------------------------
        #
        # this
        # masquerades
        # as
        # source
        # -------------------------------------------------------------

        # additional check: Filter all the nodes containing an expression
        # statement (`ast.Expr`) containing only a `ast.Name` with a `ast.Load`
        # context.
        ok = True
        for node in tree.body:
            # check if tree has anything that is not an expressions statement
            if not isinstance(node, ast.Expr):
                return True

            # we have an expression statement
            if not isinstance(node.value, ast.Name):
                return True

        # if we get here, the entire tree is composed of expression statements
        # with Name
        return False

        # Note: still imperfect. The following will be treated as code
        # -------------------------------------------------------------
        # * gork
        # -- item
        # whatever
        # -------------------------------------------------------------
        # Note: still imperfect. double comments `## hello`
        # Note: this block will *not* be treated as source
        # -------------------------------------------------------------
        # plot model residuals
        # np.ma.median(pixels, 1)
        # -------------------------------------------------------------

    except:
        return False

# def hard_wrap(filename, width=80, up_to_line=math.inf, ):
#

# remove_todo, remove_fixme, remove_commented_code
