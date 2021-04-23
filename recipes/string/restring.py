import itertools as itt
import re
import ast
import textwrap as txw
import logging

from flynt.transform.transform import transform_chunk as fstring_transform

from recipes.io import iter_lines, write_replace
from recipes.op import prepend, append
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
# RGX_PRINTF_STR = re.compile(
#     r'''(?x)
#         %
#         (?:\(\w+\))?          # mapping key (name)
#         [#0\-+ ]{0,2}         # conversion flags
#         \d*                   # min field width
#         \.?(?:\d*|\*?)      # precision
#         [diouxXeEfFgGcrsa%] # conversion type.
#         ''')

RGX_TRAILSPACE = re.compile(r'\s+\n')


def get_strings(lines):
    first = True
    for line in lines:
        match = RGX_PYSTRING.search(line)
        if match:
            yield line, match
            first = False
        elif not first:
            break


class String:
    @classmethod
    def parse(cls, block):
        itr = get_strings(block.splitlines(keepends=True))
        return cls.from_matches(itr)

    @classmethod
    def from_matches(cls, itr):
        line, match = next(itr, (None, None))
        if not match:
            raise ValueError("No string in selected text")

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


def _read_around(filename, line_nr, pre=10, post=10):
    lines = list(iter_lines(filename,
                            max(line_nr - pre, 0),
                            line_nr + post + 1,
                            strip=''))
    split = min(pre, line_nr)
    return lines[:split], lines[split:]


def get_string_block(filename, line_nr, pre=10, post=10):
    head, tail = _read_around(filename, line_nr, pre, post)
    yield from reversed(list(get_strings(head[::-1])))
    yield from get_strings(tail)


def always_true(_):
    return True


def get_code_block(filename, line_nr, pre=10, post=10, condition=always_true):

    # n = count_lines(filename)
    head, tail = _read_around(filename, line_nr, pre, post)
    strings0 = list(get_strings(head[::-1]))[::-1]
    strings1 = list(get_strings(tail))
    lines, string_matches = zip(*(*strings0, *strings1))
    lines = list(lines)
    if not lines:
        raise ValueError(f'Could not find any strings in {filename} at line {line_nr}')
    
    pre = head[:-len(strings0)]
    post = tail[len(strings1):]
    return *find_block(pre, lines, post, condition), string_matches


def find_block(pre, lines, post, condition=always_true):
    """
    Try find a parsable code block by prepending / appending lines until it
    compiles as an ast
    """
    npre, npost = len(pre), len(post)
    for i, j in sorted(itt.product(range(npre), range(npost)), key=sum):
        block = pre[(npre - i):] + lines + post[:j]
        try:
            tree = ast.parse(txw.dedent(''.join(block)))
            if condition(tree):
                return i, j, block
        except SyntaxError:
            pass

    raise ValueError('Could not get logical code block')


def _first_parsable_block(lines, join, initial=''):
    block = initial
    for line in lines:
        block = join(block, line)
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
    # block = get_code_block(filename, line_nr)
    matches = get_string_block(filename, line_nr)
    String.from_matches(matches).wrap_in_file(filename, width, expandtabs)


def strip_trailing_space(filename, ignored_=()):
    with open(filename, 'r+') as fp:
        line = fp.readline()
        mo = RGX_TRAILSPACE.search(line)
        if mo:
            fp.write(RGX_TRAILSPACE.sub('\n', line))

    # write_replace(filename, {string: RGX_TRAILSPACE.sub('\n', string)})


class GetMod(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.mod = None

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Mod):
            self.mod = node


def get_mod(tree):
    v = GetMod()
    v.visit(tree)
    return v.mod


def _convert_fstring(block, string=None, quote=None, width=80, expandtabs=True):
    if not isinstance(string, String):
        string = String.parse(block)

    # get mod part
    block = txw.dedent(block)
    tree = ast.parse(block)
    mod = get_mod(tree)
    # if v.rhs is None:
    #     raise ValueError('not found')
    original = ast.get_source_segment(block, mod)  # python >=3.8
    modstring = ast.get_source_segment(block, mod.right)

    # return f'{string.unwrapped!r} % {modstring}'
    
    quote = quote or string.quote
    # FIXME: this function is frekkin useless!
    new, changed = fstring_transform(
        f'{string.unwrapped!r} % {modstring}', quote)
    new = String.parse(new)
    new.indents = string.indents

    return original, new.wrap(width, expandtabs), changed


def convert_fstring(filename, line_nr, quote=None, width=80, expandtabs=True):

    i, j, block, strings = get_code_block(filename, line_nr)
    s = String.from_matches(zip(block[i:-j or None], strings))

    block = ''.join(block)
    origin, new, changed = _convert_fstring(block, s, quote, width, expandtabs)
    if changed:
        write_replace(filename, {origin: new})
    else:
        logger.info('String not converted.')
