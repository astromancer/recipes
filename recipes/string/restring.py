import itertools as itt
import re
import ast
import textwrap as txw
import logging

from flynt.transform.transform import transform_chunk as fstring_transform

from recipes.io import iter_lines, write_replace
from recipes.string.string import prepend, append
from recipes.logging import get_module_logger
# from recipes

# module logger
logger = get_module_logger()
logging.basicConfig()
logger.setLevel(logging.INFO)


RGX_PYSTRING = re.compile(
    r'''(?xs)
        (?P<indent>\s*)                           # indent
        (?P<marks>r?f?)                      # string type indicator
        (?P<quote>(['"]){1}(?:\4{2})?)     # quote characters
        (?P<content>.*?)                # string contents
        \3                              # closing quote
    ''')
RGX_PRINTF_STR = re.compile(
    r'''(?x)
        %
        (?:\(\w+\))?          # mapping key (name)
        [#0\-+ ]{0,2}         # conversion flags
        \d*                   # min field width
        \.?(?:\d*|\*?)      # precision
        [diouxXeEfFgGcrsa%] # conversion type.
        ''')

RGX_TRAILSPACE = re.compile(r'\s+\n')


def get_strings(block):
    for line in block.splitlines(keepends=True):
        # print(line)
        match = RGX_PYSTRING.search(line)
        if match:
            yield line, match
        else:
            break


class String:
    @classmethod
    def parse(cls, block):
        itr = get_strings(block)
        line, match = next(itr, (None, None))
        if not match:
            logger.info("No string in selected text")
            return

        # get quotation characters
        marks = match['marks']
        quote = match['quote']

        # unwrap selection
        start = match.start('marks')
        unwrapped = match['content']
        raw = line[start:]
        for line, match in itr:
            raw += line
            unwrapped += match['content']

        # strip trailing characters so we don't munging trailing content in the file
        raw = raw[:(match.end() - len(line))]
        logger.info('Parsed string:\n\t%r', raw)

        # Get indent for line from file. We have to make the first line break
        # earlier so we can use the result as a drop-in replacement
        indent = ' ' * start  # line.index(string.split('\n', 1)[0])
        indents = [indent, indent]
        return cls(raw, unwrapped, marks, quote, indents)

    def __init__(self, raw, unwrapped, marks, quote, indents):
        self.raw = raw
        self.unwrapped = unwrapped
        self.marks = marks
        self.quote = quote
        self.indents = indents

    # @property
    # def tripple(self):

    def wrap(self, width=80, expandtabs=True):
        return wrap(self.unwrapped, width,
                    self.marks, self.quote,
                    self.indents[:2], expandtabs)

    def wrap_in_file(self, filename, width, expandtabs):

        new = self.wrap(width, expandtabs)
        if self.raw != new:
            # TODO: do you need to rewrite entire file for single line changes?
            write_replace(filename, {self.raw: new})
            logger.info('rewrapped!')
        else:
            logger.info('No rewrap required')


def get_code_block(filename, line_nr, pre=10, post=10):
    # n = count_lines(filename)
    lines = list(iter_lines(filename,
                            max(line_nr - pre, 0),
                            line_nr + post + 1,
                            strip=''))
    split = min(pre, line_nr)
    head, (original, *tail) = lines[:split], lines[split:]
    #
    for aggregate, lines in (append, tail), (prepend, head[::-1]):
        block = first_parsable_block([original, *lines], aggregate)
        if block:
            return block

    raise ValueError('Could not get logical code block')


def first_parsable_block(lines, join_lines):
    block = ''
    for line in lines:
        block = join_lines(block, line)
        try:
            ast.parse(txw.dedent(block))
            return block
        except SyntaxError:
            pass


def wrap(string, width=80, marks='', quote="'", indents=('', ''), expandtabs=True):

    # add indent space for quotes
    nquote = len(quote)
    single = (nquote != 3)
    opening = marks + quote
    # every line will start with the str opening marks eg: rf"
    width -= len(opening) * single

    # add opening / closing quotes
    indents = list(indents)
    indents[0] += opening
    # unwrapped += quote

    # add indent space for quotes
    if single:
        # every line will start with the str opening marks eg: rf"
        indents[1] += opening

    # hard wrap
    lines = txw.TextWrapper(width, *indents, expandtabs,
                            replace_whitespace=False,
                            drop_whitespace=False
                            ).wrap(string)
    # add quote marks
    if single:
        lines = map(''.join, zip(lines, itt.repeat(quote)))

    return '\n'.join(lines).lstrip()


def rewrap(filename, line_nr, width=80, expandtabs=True):
    # rewrap python strings
    block = get_code_block(filename, line_nr)
    String.parse(block).wrap_in_file(filename, width, expandtabs)


def strip_trailing_space(filename, string, ignored_):
    write_replace(filename, {string: RGX_TRAILSPACE.sub('\n', string)})


class GetModArg(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.rhs = None

    def visit_BinOp(self, node):
        self.rhs = node.right


def convert_fstring(filename, line_nr, quote=None, width=80, expandtabs=True):

    block = get_code_block(filename, line_nr)
    s = String.parse(block)

    # get mod part
    block = txw.dedent(block)
    tree = ast.parse(block)
    v = GetModArg()
    v.visit(tree)
    # if v.rhs is None:
    #     raise ValueError('not found')
    quote = quote or s.quote
    modstring = ast.get_source_segment(block, v.rhs)
    new, changed = fstring_transform(f'{s.unwrapped!r} % {modstring}', quote)
    new = String.parse(new)
    new.indents = s.indents

    # from IPython import embed
    # embed(header="Embedded interpreter at 'restring.py':215")

    if changed:
        write_replace(
            filename,
            {s.raw + re.search(fr'\s*%\s*{modstring}', block)[0]:
             new.wrap()}
        )
    else:
        logger.info('String not converted.')
