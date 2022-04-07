"""
Unicode sets and helpers.
"""

# std
import functools as ftl
from collections import abc

# relative
from ..string import strings


# TODO: class for these : unicode.subscript('i=1') # 'ᵢ₌₀'
SUB_GREEK = {'β': 'ᵦ',
             'γ': 'ᵧ',
             'ρ': 'ᵨ',
             'φ': 'ᵩ',
             'χ': 'ᵪ'}

SUP_GREEK = {
    'β': 'ᵝ',
    'γ': 'ᵞ',
    'δ': 'ᵟ',
    'ε': 'ᵋ',
    'θ': 'ᶿ',
    'ι': 'ᶥ',
    'υ': 'ᶹ',
    'φ': 'ᵠ',
    'χ': 'ᵡ'
}

SUP_GREEK_FAKE = {
    'Λ': 'ᣔ',   # 'CANADIAN SYLLABICS OJIBWAY P'
    'Δ': 'ᐞ'    # 'CANADIAN SYLLABICS GLOTTAL STOP'
}


class Scripts:
    super = {}
    sub = {}


SUB_SYMBOLS = {
    '+': '₊',
    '-': '₋',
    '=': '₌',
    '(': '₍',
    ')': '₎'
}
SUP_SYMBOLS = {
    '-': '⁻',
    '+': '⁺',
    '=': '⁼',
    '(': '⁽',
    ')': '⁾'
}

nrs = Scripts()
for i, chars in enumerate(('₀₁₂₃₄₅₆₇₈₉',
                           '⁰¹²³⁴⁵⁶⁷⁸⁹')):
    n = dict(enumerate(chars))
    (nrs.sub, nrs.super)[i].update(zip(map(str, n), n.values()))


SUB_LATIN_LOWER = dict(
    a='ₐ',
    # b
    # c
    # d
    e='ₑ',
    # f
    # g
    h='ₕ',
    i='ᵢ',
    j='ⱼ',
    k='ₖ',
    l='ₗ',
    m='ₘ',
    n='ₙ',
    o='ₒ',
    p='ₚ',
    # q
    r='ᵣ',
    s='ₛ',
    t='ₜ',
    u='ᵤ',
    v='ᵥ',
    # w
    x='ₓ'
    # y
    # z
)

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
    # q
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
    C='ᒼ',  # 'CANADIAN SYLLABICS WEST-CREE M'
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
    S='ᔆ',  # CANADIAN SYLLABICS ATHAPASCAN S'
    T='ᵀ',
    U='ᵁ',
    V='ⱽ',
    W='ᵂ',
    X='ᕽ',  # 'CANADIAN SYLLABICS HK'
    # Y
    Z='ᙆ'   # 'CANADIAN SYLLABICS CARRIER Z'
)

# alphabetic
SUB_LATIN_ALPHA = {**SUB_LATIN_LOWER, **SUB_LATIN_UPPER}
SUP_LATIN_ALPHA = {**SUP_LATIN_LOWER, **SUP_LATIN_UPPER}
# alphanumeric
SUB_LATIN_ALPHANUM = {**SUB_LATIN_ALPHA, **nrs.sub}
SUP_LATIN_ALPHANUM = {**SUP_LATIN_ALPHA, **nrs.super}


class ScriptTranslate(dict):
    """(Super/sub)script translation helper"""

    def __init__(self, nrs, chars, symbols):
        super().__init__(nrs)
        self.update(zip(strings(nrs), nrs.values()))
        self.update(chars)
        self.update(symbols)
        self.__dict__.update(chars)

    def __call__(self, obj):
        return self.translate(obj)

    @ftl.cached_property
    def mappings(self):
        return str.maketrans(dict(self))

    def translate(self, obj):
        """Translate str or collections of strings to scriptcase"""
        if isinstance(obj, (str, int)):
            return str(obj).translate(self.mappings)

        if isinstance(obj, abc.Collection):
            return type(obj)(map(self.translate, obj))

        raise TypeError(f'Cannot translate object of type: '
                        f'{type(obj).__name__!r}')


superscript = superscripts = ScriptTranslate(nrs.super, SUP_LATIN_ALPHA, SUP_SYMBOLS)
subcript = subscripts = ScriptTranslate(nrs.sub, SUB_LATIN_ALPHA, SUB_SYMBOLS)
