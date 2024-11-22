"""
Manipulating string affixes.
"""


def remove_affix(string, prefix='', suffix=''):
    for i, affix in enumerate((prefix, suffix)):
        string = _replace_affix(string, affix, '', i)
    return string


def _replace_affix(string, affix, new, i):
    # handles prefix and suffix replace. (i==0: prefix, i==1: suffix)
    if affix and (string.startswith, string.endswith)[i](affix):
        w = (1, -1)[i]
        return ''.join((new, string[slice(*(w * len(affix), None)[::w])])[::w])
    return string


def remove_prefix(string, prefix):
    # str.removeprefix python 3.9:
    return remove_affix(string, prefix)


def remove_suffix(string, suffix):
    # str.removesuffix python 3.9:
    return remove_affix(string, '', suffix)


def remove_suffixes(string, suffixes, repeat=False):
    """Remove any of the suffixes"""
    for suffix in suffixes:
        new = remove_affix(string, '', suffix)
        if new != string:
            if repeat:
                string = new
            else:
                return new

    return new


def replace_prefix(string, old, new):
    """
    Substitute a prefix string.

    Parameters
    ----------
    string : str
        String to modify.
    old : str
        Prefix to replace.
    new : str
        New prefix to substitute.

    Examples
    --------
    >>> replace_prefix('foology', 'f', 'z')
    'zoology'

    Returns
    -------
    str
        String will be modified if it originally started with the `old` prefix.
    """
    return _replace_affix(string, old, new, 0)

# @doc.splice(replace_prefix)


def replace_suffix(string, old, new):
    return _replace_affix(string, old, new, 1)


def shared_prefix(strings, stops=''):
    common = ''
    for letters in zip(*strings):
        if len(set(letters)) > 1:
            break

        letter = letters[0]
        if letter in stops:
            break

        common += letter
    return common


def shared_suffix(strings, stops=''):
    return shared_prefix(map(reversed, strings), stops)[::-1]


def shared_affix(strings, pre_stops='', post_stops=''):
    prefix = shared_prefix(strings, pre_stops)
    i0 = len(prefix)
    suffix = shared_suffix([item[i0:] for item in strings], post_stops)
    return prefix, suffix

# ---------------------------------------------------------------------------- #

# def pad()