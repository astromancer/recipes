from recipes.io import write_replace
import operator as op
import re
import textwrap as txw
from recipes.io import read_line
import logging

# module logger
logging.basicConfig()
logger = logging.getLogger(__file__)
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


def rewrap(filename, string, line_nr, width=80, expandtabs=True):
    # rewrap python strings
    itr = RGX_PYSTRING.finditer(string)
    match = next(itr, None)
    if not match:
        "doesn't look like a string"
        return string

    opening = match['opening']
    closing = match['quote']
    tripple = (len(match['quote']) == 3)
    if not tripple:
        # every line will start with the str opening marks eg: rf'
        width -= (len(opening) + len(closing))

    # Get indent for line from file. We have to make the first line break
    # earlier so we can use the result as a drop-in replacement
    line = read_line(filename, line_nr)
    indent = ' ' * line.index(string.split('\n', 1)[0])
    indents = [indent, indent]

    # unwrap selection
    expand = (str, str.expandtabs)[expandtabs]
    get = op.itemgetter('content')
    s = expand(''.join(get(match), *map(get, itr)))

    # add opening / closing quotes
    indents[0] += opening
    s += closing

    if not tripple:
        indents[1] += opening

    lines = txw.TextWrapper(width, *indents[:2], expandtabs,
                            replace_whitespace=False,
                            drop_whitespace=False).wrap(s)
    if not tripple:
        lines = map(''.join, zip(lines, [*(closing * (len(lines) - 1)), '']))

    new = '\n'.join(lines).lstrip()
    if string != new:
        write_replace(filename, {string: new})
        logger.info('rewrapped!')
    else:
        logger.info('No rewrap required')
