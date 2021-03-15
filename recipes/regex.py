import pathlib


import re

from recipes.string import sub


# translate unix brace expansion patterns to regex pattern
UNIX_BRACE_TO_REGEX = str.maketrans(dict(zip('{},', '()|')))
UNIX_GLOB_TO_REGEX = {'.': r'\.',
                      '*': '.*',
                      '?': '.'}

# translate verbose mode regex to plain mode regex
RGX_VERBOSE_FLAG = re.compile(r'\(\?x\)()|(\(\?[aiLmsu]*)x([aiLmsu]*\))')
RGX_TERSE = re.compile(  # FIXME: does not compile with regex!
    r"""(?#!py/mx decomment Rev:20160225_1800)
        # Discard whitespace, comments and the escapes of escaped spaces and hashes.
          ( (?: \s+                  # Either g1of3 $1: Stuff to discard (3 types). Either ws,
            | \#.*                   # or comments,
            | \\(?=[\r\n]|$)         # or lone escape at EOL/EOS.
            )+                       # End one or more from 3 discardables.
          )                          # End $1: Stuff to discard.
        | ( [^\[(\s#\\]+             # Or g2of3 $2: Stuff to keep. Either non-[(\s# \\.
          | \\[^# Q\r\n]             # Or escaped-anything-but: hash, space, Q or EOL.
          | \(                       # Or an open parentheses, optionally
            (?:\?\#[^)]*(?:\)|$))?   # starting a (?# Comment group).
          | \[\^?\]? [^\[\]\\]*      # Or Character class. Allow unescaped ] if first char.
            (?:\\[^Q][^\[\]\\]*)*    # {normal*} Zero or more non-[], non-escaped-Q.
            (?:                      # Begin unrolling loop {((special1|2) normal*)*}.
              (?: \[(?::\^?\w+:\])?  # Either special1: "[", optional [:POSIX:] char class.
              | \\Q       [^\\]*     # Or special2: \Q..\E literal text. Begin with \Q.
                (?:\\(?!E)[^\\]*)*   # \Q..\E contents - everything up to \E.
                (?:\\E|$)            # \Q..\E literal text ends with \E or EOL.
              )        [^\[\]\\]*    # End special: One of 2 alternatives {(special1|2)}.
              (?:\\[^Q][^\[\]\\]*)*  # More {normal*} Zero or more non-[], non-escaped-Q.
            )* (?:\]|\\?$)           # End character class with ']' or EOL (or \\EOL).
          | \\Q       [^\\]*         # Or \Q..\E literal text start delimiter.
            (?:\\(?!E)[^\\]*)*       # \Q..\E contents - everything up to \E.
            (?:\\E|$)                # \Q..\E literal text ends with \E or EOL.
          )                          # End $2: Stuff to keep.
        | \\([# ])                   # Or g3of3 $6: Escaped-[hash|space], discard the escape.
        """, re.VERBOSE | re.MULTILINE)


def glob_to_regex(pattern):
    # Translate unix glob expression to regex for emulating bash wrt item
    # retrieval
    return re.compile(
        sub(pattern.translate(UNIX_BRACE_TO_REGEX), UNIX_GLOB_TO_REGEX)
    )


class Path(type(pathlib.Path())):
    """Monkey patch path object to add filename regex search feature"""

    def reglob(self, exp):
        """
        glob.glob() style searching with regex

        :param exp: Regex expression for filename
        """
        m = re.compile(exp)

        names = map(lambda p: p.name, self.iterdir())
        res = filter(m.match, names)
        res = map(lambda p: self / p, res)

        return res


def terse(pattern):
    """
    Go from verbose format multiline regex to single line terse representation
    """
    # https://stackoverflow.com/a/35641837/1098683

    if isinstance(pattern, str):
        compiler = str
    elif isinstance(pattern, re.Pattern):
        pattern = pattern.pattern
        compiler = re.compile
    else:
        err = TypeError(f'Invalid pattern object of class {type(pattern)}.')
        try:
            import regex
        except ModuleNotFoundError:
            raise err from None
        else:
            if isinstance(pattern, regex.regex.Pattern):
                pattern = pattern.pattern
                compiler = regex.compile
            else:
                raise err from None

    return compiler(RGX_VERBOSE_FLAG.sub(r'\1\2\3',
                                         RGX_TERSE.sub(detidy_cb, pattern)))


def detidy_cb(m):
    # Function pcre_detidy to convert xmode regex string to non-xmode.
    # Rev: 20160225_1800
    if m.group(2):
        return m.group(2)
    if m.group(3):
        return m.group(3)
    return ""
