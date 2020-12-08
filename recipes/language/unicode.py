# TODO: class for these : unicode.subscript('i=1') # 'ᵢ₌₀'

# SUB_SYMBOLS = '₊ 	₋ 	₌ 	₍ 	₎ 	⁻'
SUP_NRS = '⁰¹²³⁴⁵⁶⁷⁸⁹'  # list(
SUB_NRS = '₀₁₂₃₄₅₆₇₈₉'  # list(


# t = str.maketrans(''.join(map(chr, range(48, 58))), ''.join(SUP_NRS))

class UnicodeTranslate(object):
    def __init__(self, charset):
        self.__dict__.update(**charset)


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
                 x='ₓ'),
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

super = UnicodeTranslate(dict(zip(map(chr, range(48, 58)), SUP_NRS)))
