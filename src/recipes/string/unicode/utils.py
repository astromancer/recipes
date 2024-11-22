

def vertical_brace(size, text=''):
    """
    Create a multi-line right brace.

    Parameters
    ----------
    size : int
        Number of lines to span.
    text : str, optional
        Text to place on the right and vertically in center, by default ''.

    Examples
    --------
    >>> vertical_brace(5, 'Text!')
    '⎫\n'
    '⎪\n'
    '⎬ Text!\n'
    '⎪\n'
    '⎭\n'

    Returns
    -------
    str
        Multiline string brace with centred text

    """
    # TODO: recipes.strings.unicode.long_brace ???
    # Various other brace styles

    if size == 1:
        return f'}} {text}'

    if size == 2:
        return (f'⎱\n'       # Upper right or lower left curly bracket section
                f'⎰ {text} ')        # Upper left or lower right curly bracket section

    d, r = divmod(int(size) - 3, 2)
    return '\n'.join((r'⎫',             # 23AB: Right curly bracket upper hook
                      *'⎪' * d,         # 23AA Curly bracket extension
                      f'⎬ {text}',      # 23AC Right curly bracket middle piece
                      *'⎪' * (d + r),
                      r'⎭'))            # 23AD Right curly bracket lower hook


# alias
vbrace = vertical_brace
