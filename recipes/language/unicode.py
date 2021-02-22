# TODO: class for these : unicode.subscript('i=1') # 'ᵢ₌₀'

# SUB_SYMBOLS = '₊
# ₋
# ₌
# ₍
# ₎
# ⁻'
SUP_NRS = dict(zip(map(str, range(10)), '⁰¹²³⁴⁵⁶⁷⁸⁹'))
SUB_NRS = dict(zip(map(str, range(10)), '₀₁₂₃₄₅₆₇₈₉'))

SUB_LATIN = dict(a='ₐ',
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
                 x='ₓ')
#  y='ᵧ') # this is a gamma!

SUP_LATIN = dict(a='ᵃ',
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
                 z='ᶻ')

SUP_LATIN_UPPER = {
    'A': 'ᴬ',
    'B': 'ᴮ',
    # 'C': '',
    'D': 'ᴰ',
    'E': 'ᴱ',
    # 'F': '',
    'G': 'ᴳ',
    'H': 'ᴴ',
    'I': 'ᴵ',
    'J': 'ᴶ',
    'K': 'ᴷ',
    'L': 'ᴸ',
    'M': 'ᴹ',
    'N': 'ᴺ',
    'O': 'ᴼ',
    'P': 'ᴾ',
    # 'Q': '',
    'R': 'ᴿ',
    # 'S': '',
    'T': 'ᵀ',
    'U': 'ᵁ',
    'V': 'ⱽ',
    'W': 'ᵂ',
}


class ScriptTranslate(object):
    def __init__(self, chars, nrs):
        self.__dict__.update(**chars)
        self.__nrs = tuple(nrs)

    def __getitem__(self, key):
        return self.__nrs[key]


super = ScriptTranslate(SUP_LATIN, dict(zip(range(10), SUP_NRS)))
sub = ScriptTranslate(SUB_LATIN, dict(zip(range(10), SUB_NRS)))
