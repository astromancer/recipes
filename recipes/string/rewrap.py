import re
import textwrap as txw
import logging

from recipes.io import iter_lines, write_replace
from recipes.logging import get_module_logger

# module logger
logger = get_module_logger()
logging.basicConfig()
logger.setLevel(logging.INFO)


RGX_PYSTRING = re.compile(r'''(?xs)
    (?P<indent>\s*)                           # indent
    (?P<opening>
        (r?f?)                      # string type indicator
        (?P<quote>
            (['"]){1}(?:\5{2})?     # quote characters 
        )       
    )
    (?P<content>.*?)                # string contents
    \4                              # closing quote
    ''')

RGX_TRAILSPACE = re.compile(r'\s+\n')


def strip_trailing_space(filename, string, ignored_):
    write_replace(filename, {string: RGX_TRAILSPACE.sub('\n', string)})


def get_strings(filename, selection, line_nr):
    # get string part of selection
    startline = line_nr - selection.count('\n')
    # endline = max(line_nr, startline + 1)
    # match = start = None
    for line in iter_lines(filename, startline, None, strip=False):
        # print(line)
        match = RGX_PYSTRING.search(line)
        if match:
            yield line, match
        else:
            break

    #     if match and start is None:
    #         start = match.start()
    #     if not match:
    #         break
    #     #string += line
    #     unwrapped += match['content']
    # return unwrapped


def rewrap(filename, selection, line_nr, width=80, expandtabs=True):
    # rewrap python strings
    itr = get_strings(filename, selection, line_nr)
    line, match = next(itr, (None, None))
    if not match:
        logger.info("No string in selected text")
        return

    # get quotation characters
    opening = match['opening']
    closing = match['quote']
    tripple = (len(match['quote']) == 3)
    if not tripple:
        # every line will start with the str opening marks eg: rf"
        width -= (len(opening) + len(closing))

    # unwrap selection
    start = match.start('opening')
    unwrapped = match['content']
    raw = line[start:]
    for line, match in itr:
        raw += line
        unwrapped += match['content']
    
    # strip trailing newlines so we don't munge the newline in the file
    raw = raw.rstrip()
    logger.info('Wrapping string:\n\t%r', raw)

    # Get indent for line from file. We have to make the first line break
    # earlier so we can use the result as a drop-in replacement
    indent = ' ' * start  # line.index(string.split('\n', 1)[0])
    indents = [indent, indent]

    # add opening / closing quotes
    indents[0] += opening
    unwrapped += closing
    # add indent space for quotes
    if not tripple:
        indents[1] += opening

    # hard wrap
    lines = txw.TextWrapper(width, *indents[:2], expandtabs,
                            replace_whitespace=False,
                            drop_whitespace=False).wrap(unwrapped)
    # add quote marks
    if not tripple:
        lines = map(''.join, zip(lines, [*(closing * (len(lines) - 1)), '']))

    new = '\n'.join(lines).lstrip()

    if raw != new:
        # TODO: do you need to rewrite entire file for single line changes?
        write_replace(filename, {raw: new})
        logger.info('rewrapped!')
    else:
        logger.info('No rewrap required')
