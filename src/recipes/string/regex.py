
# std
import re
import sys
import pathlib
import operator as op

# relative
from . import sub


# Patterns
# ---------------------------------------------------------------------------- #

# translate verbose mode regex to plain mode regex
RGX_VERBOSE_FLAG = re.compile(r'\(\?x\)()|(\(\?[aiLmsu]*)x([aiLmsu]*\))')
RGX_TERSE = re.compile(  # FIXME: does not compile with regex!
    r"""(?xm)
        # Discard whitespace, comments and the escapes of escaped spaces and hashes.
        ( (?:                        # $1: Stuff to discard (3 types). 
            \s+                      # Either ws,
          | \#.*                     #   or comments,
          | \\(?=[\r\n]|$)           #   or lone escape at EOL/EOS.
          )+                         # repeat discardable.
        )                            # End $1: Stuff to discard.
        |
        ( [^\[(\s#\\]+               # Or g2of3 $2: Stuff to keep. Either non-[(\s# \\.
          | \\[^# Q\r\n]               # Or escaped-anything-but: hash, space, Q or EOL.
          | \(                         # Or an open parentheses, optionally
            (?:\?\#                  # comment group.
               [^)]*             
               (?:\)|$)              # end comment group
            )?   
          | \[\^?\]?                   # Or Character class. Allow unescaped ] if first char.
            [^\[\]\\]*               # Zero or more non-[]
            (?:                      # Begin unrolling loop {((special1|2) normal*)*}.
              (?: 
                \[(?:                #  special: "[", optional [:POSIX:] char class.
                    :\^?\w+:
                \])?            
              )        
              [^\[\]\\]*             # Zero or more non-[]
            )* 
          (?:\] | \\?$)              # End character class with ']' or EOL (or \\EOL).
        )                          # End $2: Stuff to keep.
        | 
        \\([# ])                 #  or $3: Escaped-[hash|space], discard the escape.
    """
)

# matchers for regex groups
RGX_NAMED_GROUP = re.compile(r'\((\?P<\w+>)')
# RGX_UNGROUP = re.compile(r'\(\?P<[a-zA-Z]+>([^)]+)\)')


# translate unix brace expansion patterns to regex pattern
UNIX_BRACE_TO_REGEX = str.maketrans(dict(zip('{},', '()|')))
UNIX_GLOB_TO_REGEX = {'.': r'\.',
                      '*': '.*',
                      '?': '.'}


# utils
# ---------------------------------------------------------------------------- #
def match_all(strings, pattern):
    matches = {}
    matcher = re.compile(pattern)
    for i, string in enumerate(strings):
        m = matcher.match(string)
        if m:
            matches[i] = m.group()
    return matches


def split_iter(string, sep=r'\s+'):
    # source : https://stackoverflow.com/a/9770397
    regex = f'(?:^|{sep})((?:(?!{sep}).)*)'
    for match in re.finditer(regex, string):
        yield match.group(1)


# Regex mutaters
# ---------------------------------------------------------------------------- #
def _resolve(pattern):

    if isinstance(pattern, str):
        return pattern, str

    if isinstance(pattern, re.Pattern):
        return pattern.pattern, re.compile

    if (regex := sys.modules.get('regex')) and isinstance(pattern, regex.regex.Pattern):
        return pattern.pattern, regex.compile

    raise TypeError(f'Invalid pattern object of class {type(pattern)}.')


def unname(pattern, noncapture=False):
    """
    Remove name references from groups
    (?P<name>)
    """
    pattern, compiler = _resolve(pattern)
    sub = '(?:' if noncapture else '('
    return compiler(RGX_NAMED_GROUP.sub(sub, pattern))


def unflag(pattern):
    """
    Remove in-pattern flags
    (?x)
    """
    pattern, compiler = _resolve(pattern)
    return compiler(RGX_VERBOSE_FLAG.sub(r'\1\2\3', pattern))


# def ungroup(pattern, n=1):
#     pattern, compiler = _resolve(pattern)
#     return compiler(RGX_UNGROUP.sub(fr'\{n}', pattern))


def uncomment(pattern):
    """
    Go from verbose format multiline regex to single line representation
    with all comments removed.
    """
    # https://stackoverflow.com/a/35641837/1098683

    pattern, compiler = _resolve(pattern)
    return compiler(unflag(RGX_TERSE.sub(_uncomment, pattern)))


def _uncomment(match):
    # Function to convert verbose (x-mode) regex string to non-verbose.
    if match.group(2):
        return match.group(2)
        # return m.group(3)
    return ""


# # alias
# def terse(pattern, uncomment=True, ungroup=True):
    


# Translate to regex
# ---------------------------------------------------------------------------- #
def glob_to_regex(pattern):  # bash_to_regex
    # Translate unix glob expression to regex for emulating bash wrt item
    # retrieval
    pattern, compiler = _resolve(pattern)
    return compiler(
        sub(pattern.translate(UNIX_BRACE_TO_REGEX), UNIX_GLOB_TO_REGEX)
    )


# Path subclass that supports regex filename searches
# ---------------------------------------------------------------------------- #
class Path(type(pathlib.Path())):
    """Monkey patch path object to add filename regex search feature"""

    def reglob(self, exp):
        """
        glob.glob() style searching with regex

        :param exp: Regex expression for filename
        """
        m = re.compile(exp)

        names = map(op.attergetter('name'), self.iterdir())
        res = filter(m.match, names)
        return map(lambda p: self / p, res)
