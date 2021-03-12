import re
import textwrap as txw


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


def rewrap(string, width=80, expandtabs=True):
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

    s = match['content']
    indents = [match['indent']]
    expand = (str, str.expandtabs)[expandtabs]
    for match in itr:
        s += match['content']
        indents.append(expand(match['indent']))

    # infer initial indent from subsequent indents. We have to make the first
    # line break earlier so we can use the result as a drop-in replacement
    if not indents[0]:
        indents[0] = indents[1]

    # add opeing / closing quotes
    indents[0] += opening
    s += closing

    if not tripple:
        indents[1] += opening

    lines = txw.TextWrapper(width, *indents[:2], expandtabs,
                            replace_whitespace=False,
                            drop_whitespace=False).wrap(s)
    if not tripple:
        lines = map(''.join, zip(lines, [*(closing * (len(lines) - 1)), '']))

    return ''.join(lines).lstrip()
