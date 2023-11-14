"""
Special casing for strings.
"""

import re


# ---------------------------------------------------------------------------- #
REGEX_CAPS = re.compile('([A-Z])')
REGEX_SPACE = re.compile(r'\s+')


# ---------------------------------------------------------------------------- #

def snake_case(string):
    new, _ = REGEX_CAPS.subn(r'_\1', string.replace(' ', '_'))
    return new.lstrip('_').lower()


def pascal_case(string):
    return string.replace('_', ' ').title().replace(' ', '')


def camel_case(string):
    string = pascal_case(string)
    return string[0].lower() + string[1:]


def kebab_case(string):
    return string.replace(' ', '-').replace('_', '-')


def title(string, ignore=()):
    """
    Title case string with optional ignore patterns.

    Parameters
    ----------
    string : str
        sttring to convert to titlecase
    ignore : tuple of str
        These elements of the string will not be title cased
    """
    if isinstance(ignore, str):
        ignore = [ignore]

    ignore = tuple(map(str.strip, ignore))
    subs = {f'{s.title()} ': f'{s} ' for s in ignore}
    new = sub(string.title(), subs)
    if string.endswith(ignore):  # ths one does not get subbed above due to spaces
        head, last = new.rsplit(maxsplit=1)
        return f'{head} {last.lower()}'
    return new


def strike(text):
    """
    Produce strikethrough text using unicode modifiers.

    Parameters
    ----------
    text : str
        Text to be struck through

    Examples
    --------
    >>> strike('hello world')
    '̶h̶e̶l̶l̶o̶ ̶w̶o̶r̶l̶d'

    Returns
    -------
    str
        strikethrough text
    """
    return '\u0336'.join(text) + '\u0336'
    # return ''.join(t+chr(822) for t in text)


def monospaced(text):
    """
    Convert all contiguous whitespace into single space and strip leading and
    trailing spaces.

    Parameters
    ----------
    text : str
        Text to be re-spaced

    Returns
    -------
    str
        Copy of input string with all contiguous white space replaced with
        single space " ".
    """
    return REGEX_SPACE.sub(' ', text).strip()
