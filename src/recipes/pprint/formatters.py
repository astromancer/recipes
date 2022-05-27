# std
import math
import numbers
import warnings
from fractions import Fraction

# third-party
import numpy as np

# relative
from ..string import sub
from .. import unicode
from ..dicts import AttrReadItem
from ..utils import duplicate_if_scalar
from ..math import order_of_magnitude, signum
from .callers import describe


# unicode
UNICODE_TRANSLATIONS = {'inf':  '∞',    # '\N{INFINITY}',
                        '-':    '−'}    # '\N{MINUS SIGN}',
UNICODE_MULTIPLIERS = {'x':   '×',      # '\N{MULTIPLICATION SIGN}'
                       '.':   '·'}      # '\N{MIDDLE DOT}'
# ⏨  Decimal exponent symbol
# ⒑  Number Ten Full Stop
# ⑽ Parenthesized Number Ten

# LaTeX
LATEX_TRANSLATIONS = {'inf':    r'\infty'}
LATEX_MULTIPLIERS = {'x':      r'\times',
                     '.':      r'\cdot'}

#
MASKED_CONSTANT = '--'

# SI metric prefixes
METRIC_PREFIXES = {
    -24: 'y',
    -21: 'z',
    -18: 'a',
    -15: 'f',
    -12: 'p',
    -9:  'n',
    -6:  'µ',
    -3:  'm',
    0:   '',
    +3:  'k',
    +6:  'M',
    +9:  'G',
    +12: 'T',
    +15: 'P',
    +18: 'E',
    +21: 'Z',
    +24: 'Y'
}

# decimal, scientific, metric
KNOWN_FORMATS = {'ascii', 'unicode', 'latex', 'metric'}


def empty_string(_):
    return ''


def resolve_sign(sign, allowed=' -+'):
    if sign is None:
        return ' '

    if isinstance(sign, bool):
        return '-+'[sign]

    if isinstance(sign, str) and ((allowed is any) or (sign in allowed)):
        return sign

    raise ValueError(f'Invalid sign {sign!r}. Use one of {tuple(allowed)}.')


class Masked:
    """Format masked constants."""

    def __init__(self, string=MASKED_CONSTANT):
        self.constant = str(string)

    def __call__(self, _):
        return self.constant


class Percentage:
    """
    Format a number and append the percentage of a total between brackets.
    """

    def __init__(self, total, fmt_nr, precision=0, brackets='()'):
        self.total = float(total)
        self.formatter = fmt_nr
        self.precision = int(precision)  # for percentage value
        # self.brackets = str(brackets)
        fmt_p = f'{{f}}:.{self.precision}%'.join(brackets)
        self._fmt = f'{{n}} {fmt_p}'

    def __call__(self, n):
        return self._fmt.format(n=self.formatter(n), f=n / self.total)


class BaseNumeric:
    def __call__(self, n):
        """
        n: int or float
            the number to format
        """
        # handel masked values
        # if isinstance(n, np.ma.core.MaskedConstant):
        #     return '--'

        # ensure we have a scalar
        if not isinstance(n, numbers.Real):
            raise ValueError('Only scalars are accepted by this function.')

        # handle nans
        if math.isnan(n):
            return 'nan'


class Decimal:
    """Decimal number formatter."""

    def __init__(self, precision=None, significant=3, sign='-',
                 thousands='', shorten=True):  # tail0
        """
        Decimal representation of float as str up to given number of significant
        digits (relative to order of magniture), or decimal precision
        (absolute). Support for minimalist `shorten` representations as well as
        optional left- and right padding and unicode representation of
        minus/infinity (−/∞) included.

        Parameters
        ----------
        precision: int, optional
            if int:
                Decimal precision (absolute) for format.
            if None, the default:
                precision = 1 if the abs(number) is larger than 1. eg. 100.1
                Otherwise it is chosen such that at least 3 significant digits
                are shown: eg: 0.0000345 or 0.985
        significant : int, optional
            If precision is not given, this gives the number of non-zero digits
            after the decimal point that will be displayed. This argument allows
            specification of dynamic precision values which is useful when
            dealing with numbers that have a large dynamic range.
        sign: str or bool, optional
            "-" or True: always sign.
            "+" or False: only sign negative numbers.
            " " or None: sign negative, pre-space positive.
        thousands: str, optional
            Thousands separator.
        shorten : {True, False, -1}
            * If True, the default, redundant zeros after decimal point will be
                stripped to yield a more compact representation of the same
                number.
            * If -1, whitespaces will replace the redundant trailing zeros and
                decimal point.
            * If False, the number is left unaltered.


        Returns
        -------
        str

        Examples
        --------
        >>> decimal(2.0000001, 3)
        '2'
        >>> decimal(3.14159265, 5)
        '3.14159'
        """

        self.precision = precision
        self.significant = int(significant)
        self.thousands = str(thousands)
        self.sign = resolve_sign(sign)
        self.shorten = bool(shorten)

    def __call__(self, n, precision=None):
        """
        n: int or float
            the number to format
        """

        # ensure we have a scalar
        if not isinstance(n, numbers.Real):
            raise ValueError(f'Only scalars are accepted by this function, not'
                             f' {type(n)}.')

        # handle nans
        if math.isnan(n):
            return 'nan'

        precision = self._sanitize_precision(precision, n)

        # format the number
        spec = f'{self.sign}{","[:bool(self.thousands)]}.{precision}f'
        s = format(n, spec).replace(',', self.thousands)

        # strip redundant zeros
        # n_stripped = 0
        # width = len(s)
        if self.shorten and precision > 0:
            # remove redundant zeros
            s = s.rstrip('0').rstrip('.')
            # n_stripped = width - len(s)

        # Right pad for when numbers are displayed to various precisions and the
        # should form a block. eg. nrs followed by a 1σ uncertainty, and we want to
        # line up with the '±'.
        # eg.:
        #   [-12   ± 1.2,
        #      1.1 ± 0.2 ]

        # if right_pad >= max(precision - n_stripped, 0):
        #     # compute required width of formatted number string
        #     m = m or order_of_magnitude(n)
        #     w = sum((int(bool(sign) & (n < 0)),
        #              max(left_pad, m + 1),  # width lhs of '.'
        #              max(right_pad, precision),  # width rhs of '.'
        #              int(precision > 0)))  # '.' expected in formatted str?

        #     s = s.ljust(w, right_pad_char)

        return s

    def _sanitize_precision(self, precision, n):
        # decide default precision
        m = None
        precision = precision or self.precision
        if (precision is None):  # or (left_pad > 0) or (right_pad > 0):
            # order of magnitude and `significant` determines precision
            m = order_of_magnitude(n)
            if math.isinf(m):
                m = 0
            precision = int(self.significant) - min(m, 1) - 1

        # only positive precisions make sense for decimal format
        if precision < 0:
            warnings.warn(f'Negative precision not allowed for '
                          f'{describe(type(self))}. Setting precision to 0.')
            return 0
        return precision

    @classmethod
    def as_percentage_of(cls, total, **kws):
        return Percentage(total, cls(**kws))

    def latex(self, n):
        # TODO: spaces for thousands also ignore padding ???
        return sub(self(n), LATEX_TRANSLATIONS)

    def ascii(self, n):
        return self(n)

    def unicode(self, n):
        """
        prefer unicode minus '−' over '-'
        prefer unicode infinity '∞' over 'inf'

        Parameters
        ----------
        n : [type]
            [description]

        Examples
        --------
        >>> 
        """
        return sub(self(n), UNICODE_TRANSLATIONS)

    def metric(self, n):
        return self(n)

    def shortest(self, n, choices=KNOWN_FORMATS):
        """
        Most compact representation possible from amongst formats `choices`.

        Parameters
        ----------
        n : [type]
            [description]

        Examples
        --------
        >>> 

        Returns
        -------
        [type]
            [description]
        """


class Scientific(Decimal):
    """
    Scientific numeral representation strings in various formats.
    """

    def __init__(self, significant=5, sign=False, times='x', thousands='',
                 shorten=True):
        """

        Parameters
        ----------
        n: numbers.Real
            {}
        significant: int
            {}
        sign: str, bool
            {}
        times: str
            style to use for multiplication symbol.
            * If value is either 'x' or '.':
                The symbol used is decided based on the unicode and latex flags
                as per the following table:
                    unicode:    '×'         or      '·'
                    latex:      '\\times'    or      '\\cdot'
                    str:         'x'        or      '*'
            * using 'E' or 'e' will switch to E-notation style. eg.: 1.3e-12
            * Any other str may be passed in which case it will be used verbatim.
        shorten: bool
            {}


        Returns
        -------
        str

        Examples
        --------
        >>> 

        References
        ----------
        [1] https://en.wikipedia.org/wiki/Scientific_notation


        """

        super().__init__(None, significant, sign, thousands, shorten)
        self.times = str(times)

        # TODO: spacing options.

        #     unicode: bool
        #     prefer unicode minus symbol '−' over '-'
        #     prefer unicode infinity symbol  '∞' over 'inf'
        #     prefer unicode multiplication symbol '×' over 'x'
        # latex:
        #     represent the number as a latex string:
        #     eg:. '$1.04 \\times 10^{-12}$'
        # engineering: bool
        #     Prefer representation where exponent is a multiple of 3. Essentially
        #     scientific notation with base 1000.

    def __call__(self, n, times=None, base='10', exp=unicode.superscript):
        # TODO: defaults at module_level:
        # scientific notation
        # n_ = abs(n)
        m = order_of_magnitude(n)  # might be -inf
        p = self.significant

        # first get the ×10ⁿ part
        times = times or self.times
        if self.shorten is True:
            if (m == 0):
                times = base = ''
            if m in {0, 1}:
                exp = empty_string
            if (-m <= self.significant < 3):
                # 0.1 is shorter than 1e-1
                # 0.01 same as        1e-2  but more readable

                # fucked = super().__call__(n * (10 ** -m), p)
                # this = super().__call__(n, p)
                # from IPython import embed
                # embed(header="Embedded interpreter at 'src/recipes/pprint/formatters.py':375")
                # raise ValueError()
                m = 0
                base = times = ''
                exp = empty_string
                # p = self.significant + 1

        # coefficient / mantissa / significand
        mantissa = super().__call__(n * (10 ** -m), p)  # str

        # concatenate
        return ''.join([mantissa, times, base, str(exp(m))])

    def ascii(self, n):
        return self(n, 'e', '', int)

    def unicode(self, n):
        return self(n, UNICODE_MULTIPLIERS.get((t := self.times), t),
                    # '\N{DECIMAL EXPONENT SYMBOL}' <-  ugly: '⏨⁵'
                    # '\N{NUMBER TEN FULL STOP}'    <-  this maybe ok: "⒑⁵"
                    '10',
                    unicode.superscript)

    def latex(self, n):
        return self(n, LATEX_MULTIPLIERS.get((t := self.times), t),
                    '10', '{{{:d}}}'.format)


class Metric:
    """
    Metric style format like "12.1 kJ" or "42.67 Gb".
    """

    def __init__(self, significant=None, base=10, unit=''):
        self.significant = significant
        self.base = int(base)
        self.unit = str(unit)

    def __call__(self, n):
        """
        Format a number in engineering format

        Parameters
        ----------
        value
        significant
        base
        unit

        Returns
        -------

        """
        # significant = int(significant)
        sign = signum(n)
        n = abs(n)
        if sign == 0:
            return str(n)

        pwr = math.log(n) / math.log(self.base)
        pwr3 = int((pwr // 3) * 3)
        sig = self.significant or [0, 1][pwr3 < 0]
        mantissa = n / (self.base ** pwr3)
        return f'{mantissa:.{sig:d}f} {METRIC_PREFIXES[pwr3]}{self.unit}'


Engineering = Metric


class Conditional:
    """
    Switch between format styles based on some conditional.
    """

    def __init__(self, test, test_args, true, false=format, **kws):
        """

        Parameters
        ----------
        test: callable
            If True, apply `properties` after formatting with `formatter`
        test_args: tuple, object
            Arguments passed to the test function
        true, false: callable
            The formatter to use to format the object if the test evaluates
            True / False
        kws:
            Keywords passed to the test

        Examples
        --------
        >>> Conditional(op.le, 100, '{:4.1+f|g}', '{:4.1f|y}')

        """
        self.test = test
        self.args = tuple(duplicate_if_scalar(test_args, 1, raises=False))
        self.kws = kws
        assert callable(true)
        assert callable(false)
        self.formatters = (false, true)

    def __call__(self, obj):
        """
        Format the object and apply the colour / properties

        Parameters
        ----------
        obj: object
            The object to be formatted

        Returns
        -------

        """
        tf = self.test(obj, *self.args, **self.kws)
        if not isinstance(tf, bool):
            raise TypeError(f'Test {describe(self.test)} for formatter '
                            f'{self.__class__.__name__} returned non-boolean '
                            f'value {tf!r} of type {type(tf)}.')

        return self.formatters[tf](obj)


def oom_switch(n, log_switch):
    return abs(order_of_magnitude(n)) >= log_switch


class Numeric(Conditional):
    """
    A hybrid numberic formatter that switches between decimal and scientific
    formats based on the order of magnitude of the onput, and the predefined
    defined `log_switch` values.

    Parameters
    ----------
    Scientific : [type]
        [description]

    Examples
    --------
    >>> 
    """

    def __init__(self, precision=3, significant=3, log_switch=5,
                 sign='-', times='x', thousands='', shorten=True):
        """


        Parameters
        ----------
        log_switch: int # TODO: tuple  
            Controls switching between decimal/scientific notation. Scientific
            notation is triggered if `abs(math.log10(abs(n))) > switch`.

        shorten
            TODO: If shorten = True
            Default is chosen in such a way that the representation of the number
            is as s hort as possible. eg: '1.01445 × 10²' can be more compactly
            represented as '101.445'; 1000 can be more compactly represented as
            10³ or 1K depending on your tastes or needs.
        times
        sign


        Examples
        --------
        >>> 

        Returns
        -------
        str
            [description]
        """

        super().__init__(
            oom_switch, log_switch,
            Scientific(significant, sign, times, thousands, shorten),
            Decimal(precision, significant, sign, thousands, shorten)
        )


class FractionOf:

    templates = dict(
        ascii=('{n}{symbol}', '{n}{symbol}/{d}'),
        unicode=('{n}{symbol}', '{n}{symbol}/{d}'),
        latex=('${n}{symbol}$', r'$\frac{{{n}{symbol}}}{{{d}}}$')
    )

    def __init__(self, symbols=(), **kws):
        symbols = {k: str(v) for k, v in dict(symbols, **kws).items()}
        assert symbols.keys() == {'ascii', 'unicode', 'latex'}
        self.symbols = AttrReadItem(symbols)

    def __call__(self, f, style='ascii'):
        return self.format(f, style)

    
    def format(self, f, style='ascii'):
        s = self._format(f, style)
        if (style == 'latex') and s[0] != s[-1] != '$':
            return s.join('$$')
        return s
        
    def _format(self, f, style='ascii'):

        if f == 0:
            return '0'

        if f == 1:
            return self.symbols[style]

        if not isinstance(f, Fraction):
            f = Fraction(f)

        itmp, ftmp = self.templates[style]

        f = f.limit_denominator()
        n = n if ((n := f.numerator) != 1) else ""

        if ((d := f.denominator) == 1):
            return itmp.format(n=n, symbol=self.symbols[style], d=d)

        return ftmp.format(n=n, symbol=self.symbols[style], d=f.denominator)

    def format_mpl(self, f, _pos=None):
        return self.format(f, 'latex')
    
    def ascii(self, f, _pos=None):
        return self.format(f, 'ascii')

    def latex(self, f, _pos=None):
        return self.format(f, 'latex')#.join('$$')

    def unicode(self, f, _pos=None):
        return self.format(f, 'unicode')


class FractionOfPi(FractionOf):
    def __init__(self):
        super().__init__(ascii='pi',
                         unicode='π',
                         latex=r'\pi')
        
    def from_radian(self, n, _pos=None, style='latex'):
        return self.format(n / math.pi, style)


def frac_of(f, symbol, i_template='{n}{symbol}', f_template='{n}{symbol}/{d}'):
    # i_template='{n}{symbol}', f_

    if f == 0:
        return '0'

    if f == 1:
        return symbol

    f = f.limit_denominator()
    n = n if ((n := f.numerator) != 1) else ""

    if ((d := f.denominator) == 1):
        return i_template.format(n=n, symbol=symbol, d=d)

    return f_template.format(n=n, symbol=symbol, d=f.denominator)

# "½" #  onehalf # VULGAR FRACTION ONE HALF
# "⅓"	#U2153 # VULGAR FRACTION ONE THIRD
# "¼" #  onequarter # VULGAR FRACTION ONE QUARTER
# "⅕"	#U2155 # VULGAR FRACTION ONE FIFTH
# "⅙"	#U2159 # VULGAR FRACTION ONE SIXTH
# "⅐"	#U2150 # VULGAR FRACTION ONE SEVENTH
# "⅛"	#U215B # VULGAR FRACTION ONE EIGHTH
# "⅑"	#U2151 # VULGAR FRACTION ONE NINTH
# "⅒"	#U2152 # VULGAR FRACTION ONE TENTH
# "⅔"	#U2154 # VULGAR FRACTION TWO THIRDS
# "⅖"	#U2156 # VULGAR FRACTION TWO FIFTHS
# "¾" #  threequarters # VULGAR FRACTION THREE QUARTERS
# "⅗"	#U2157 # VULGAR FRACTION THREE FIFTHS
# "⅜"	#U215C # VULGAR FRACTION THREE EIGHTHS
# "⅘"	#U2158 # VULGAR FRACTION FOUR FIFTHS
# "⅚"	#U215A # VULGAR FRACTION FIVE SIXTHS
# "⅝"	#U215D # VULGAR FRACTION FIVE EIGHTHS
# "⅞"	#U215E # VULGAR FRACTION SEVEN EIGHTHS
# "↉"	#U2189 # VULGAR FRACTION ZERO THIRDS
