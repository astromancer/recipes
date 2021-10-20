"""
Unicode sets and helpers.
"""

# std
import functools as ftl
from collections import abc

# relative
from ..string import strings


# TODO: class for these : unicode.subscript('i=1') # 'ᵢ₌₀'


SUB_SYMBOLS = {
    '+': '₊',
    '-': '₋',
    '=': '₌',
    '(': '₍',
    ')': '₎'
}
SUP_SYMBOLS = {
    '-': '⁻',
}

#

SUP_NRS = dict(enumerate('⁰¹²³⁴⁵⁶⁷⁸⁹'))
SUB_NRS = dict(enumerate('₀₁₂₃₄₅₆₇₈₉'))

SUB_LATIN_LOWER = dict(
    a='ₐ',
    e='ₑ',
    h='ₕ',
    j='ⱼ',
    k='ₖ',
    l='ₗ',
    m='ₘ',
    n='ₙ',
    o='ₒ',
    p='ₚ',
    r='ᵣ',
    s='ₛ',
    t='ₜ',
    u='ᵤ',
    v='ᵥ',
    x='ₓ'
)
#  y='ᵧ') # this is a gamma!
SUB_LATIN_UPPER = {}

SUP_LATIN_LOWER = dict(
    a='ᵃ',
    b='ᵇ',
    c='ᶜ',
    d='ᵈ',
    e='ᵉ',
    f='ᶠ',
    g='ᵍ',
    h='ʰ',
    i='ⁱ',
    j='ʲ',
    k='ᵏ',
    l='ˡ',
    m='ᵐ',
    n='ⁿ',
    o='ᵒ',
    p='ᵖ',
    r='ʳ',
    s='ˢ',
    t='ᵗ',
    u='ᵘ',
    v='ᵛ',
    w='ʷ',
    x='ˣ',
    y='ʸ',
    z='ᶻ'
)

SUP_LATIN_UPPER = dict(
    A='ᴬ',
    B='ᴮ',
    # C= '',
    D='ᴰ',
    E='ᴱ',
    # F= '',
    G='ᴳ',
    H='ᴴ',
    I='ᴵ',
    J='ᴶ',
    K='ᴷ',
    L='ᴸ',
    M='ᴹ',
    N='ᴺ',
    O='ᴼ',
    P='ᴾ',
    # Q= '',
    R='ᴿ',
    # S= '',
    T='ᵀ',
    U='ᵁ',
    V='ⱽ',
    W='ᵂ',
)


SUP_LATIN = {**SUP_LATIN_LOWER, **SUP_LATIN_UPPER}
SUB_LATIN = {**SUB_LATIN_LOWER, **SUB_LATIN_UPPER}


class ScriptTranslate(dict):
    """(Super/sub)script translation helper"""

    def __init__(self, nrs, chars, symbols):
        super().__init__(nrs)
        self.update(zip(strings(nrs), nrs.values()))
        self.update(chars)
        self.update(symbols)
        self.__dict__.update(chars)

    @ftl.cached_property
    def mappings(self):
        return str.maketrans(dict(self))

    def translate(self, collection):
        """Translate str or collections of strings to scriptcase"""
        if isinstance(collection, str):
            return collection.translate(self.mappings)

        if isinstance(collection, abc.Collection):
            return type(collection)(map(self.translate, collection))

        raise TypeError(f'Cannot translate object of type: '
                        f'{type(collection).__name__!r}')


superscripts = ScriptTranslate(SUP_NRS, SUP_LATIN, SUP_SYMBOLS)
subscripts = ScriptTranslate(SUB_NRS, SUB_LATIN, SUB_SYMBOLS)
