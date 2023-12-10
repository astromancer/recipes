"""
Pretty formatting of numbers and numeric arrays (with uncertainties) in various
human readable forms.
"""

# This module designed for convenience and is *not* speed tested (yet)


# std
import re
import math
import pprint
import numbers
import warnings
import itertools as itt
from collections import namedtuple

# third-party
import numpy as np

# relative
from .. import op
from ..functionals import echo0
from ..array.utils import vectorize
from ..string import unicode as uni
from ..utils import duplicate_if_scalar
from ..math import order_of_magnitude, signum


# ---------------------------------------------------------------------------- #
# note: unicode literals below python3 only!
# see: https://docs.python.org/3/howto/unicode.html

HMS = namedtuple('HMS', list('hms'))
TIME_DIVISORS = list(itt.accumulate((1, 60, 60, 24, 30, 12), op.mul))[::-1]

REGEX_YMDHMS_PRECISION = re.compile(r'([yMdhms])\.?(\d)?')
REGEX_YMDHMS_SPEC = re.compile(r'''(?x)
    # (?P<sep>[^`:\s]?)                           
    (?P<tail_unit>[yMdhms])
    (\.?)(?P<precision>\d)?
    (?P<short>\??)
    ''')
# REGEX_YMDHMS_SPEC = re.compile(r'''(?x)
#     (?P<base_unit>[yMdhms]?)
#     :?|[yMdhms]{1,5}?
#     (?P<tail_unit>[yMdhms])
#     (?P<precision>\.?(\d)?)
#     ''')
# SEP_SPEC = {'^': uni.superscripts.translate('ymdhms'),
# '`': ''


# Unicode
# UNI_PWR = dict(enumerate('²³⁴⁵⁶⁷⁸⁹', 2))  # '¹²³⁴⁵⁶⁷⁸⁹'
# UNI_NEG_PWR = '⁻'  # '\N{SUPERSCRIPT MINUS}'
# UNI_PM = '±'
YMDHMS_ASCII = ('y', 'M', 'd ', 'h', 'm', 's')
YMDHMS_SUPER = ('ʸ', 'ᴹ', 'ᵈ ', 'ʰ', 'ᵐ', 'ˢ')
# uni.superscripts.translate(YMDHMS_ASCII)

PRODUCT_SYMBOLS = {'x': '\N{MULTIPLICATION SIGN}',  # '×' # u'\u00D7'
                   '.': '\N{MIDDLE DOT}'}           # '·' # u'\u00B7'
PRODUCT_SYMBOLS_LATEX = {'x': R'\times',
                         '.': R'\cdot'}
INFINITY_SYMBOLS = dict(latex=R'\infty',
                        unicode='\N{INFINITY}',     # '∞' # u'\u221E'
                        ascii='inf')

# '\N{MINUS SIGN}'              '−'     u'\u2212'
# '\N{PLUS-MINUS SIGN}'         '±'


# The SI metric prefixes
METRIC_PREFIXES = {
    -24: 'y',
    -21: 'z',
    -18: 'a',
    -15: 'f',
    -12: 'p',
    -9:  'n',
    -6:  'µ',
    -3:  'm',
    0:  '',
    +3:  'k',
    +6:  'M',
    +9:  'G',
    +12: 'T',
    +15: 'P',
    +18: 'E',
    +21: 'Z',
    +24: 'Y'
}


#  centi-, deci-, deka-, and hecto-) ???

# Regex matchers for decimal and scientific notation
# SCI_SRE = re.compile('[+-]?\d\.?\d?e[+-]?(\d\d)', re.ASCII)
# DECIMAL_SRE = re.compile('[+-]?\d+\.(0*)[1-9][\d]?', re.ASCII)

# ---------------------------------------------------------------------------- #

def leading_decimal_zeros(n):
    """
    Number of zeros following the decimal point and preceding the first non-zero
    digit.

    Parameters
    ----------
    n: any python scalar

    Returns
    -------

    """
    m = order_of_magnitude(n)
    return 0 if (m > 0 or math.isinf(m)) else -m - 1


def get_significant_digits(x, n=3):
    """
    Return the first `n` non-zero significant digits.

    Parameters
    ----------
    x: numers.Real
        Any scalar number.
    n: int
        Number of significant digits to return

    Examples
    --------
    >>> get_significant_digits(1238488290, 3)
    (124, 9)

    Returns
    -------
    nrs: int
        The `n` significant digits as a integer number
    m: int
        order of magnitude of `x`
    """
    if not isinstance(x, numbers.Real):
        raise ValueError('Only scalars are accepted by this function.')

    m = order_of_magnitude(x)
    nrs = round(x * 10 ** (n - m - 1))
    return nrs, m


def _check_pad(pad):
    if isinstance(pad, numbers.Integral):
        char = ' '
    else:
        pad, char = pad
        pad = int(pad)
        char = str(char)

    if len(char) != 1:
        raise ValueError('padding string should be a single character')

    return pad, char


def to_sexagesimal(t, base_unit='h', precision='s'):
    """
    Convert time in seconds to tuple in base 60 units. Basic usage will
    result in a 3-tuple with floats for (hours, minutes, seconds). 

    For negative input numbers, all elements in the returned tuple will be 
    negative.

    Parameters
    ----------
    t : float
        time in seconds
    base_unit : {'h', 'm', 's'}, optional
        The unit of the leftmost number in the tuple, by default 'h' If the time
        is desired in units of (minutes, seconds), for example, use
        `base_unit='m'` and `precision='s'`. Using `base_unit='s'` will simply
        wrap the input number in a tuple.
    precision : str or int, optional
        The unit and/or numerical precision for the conversion, by default 's'.
        If str, should start with one of 'h', 'm', or 's' and optionally end on
        a digit 0-9. Eg: 'h1' will return the number as a string in units of
        hours with a decimal precision of 1, while 's8' will return the number
        as an sexagesimal (hms) string of with a decimal precision of 8. If no
        digit is given, eg. 's', no rounding will be done.

    Returns
    -------
    tuple
        Sexagesimal representation of the number.
    """
    return tuple(_to_sexa(t, base_unit, precision))[::-1]

    # m, s = divmod(t, 60)
    # h, m = divmod(m, 60)
    # return HMS(h, m, s)


# alias
sexagesimal = to_sexagesimal


def _to_sexa(t, base_unit='h', precision='s'):
    # generator that computes sexagesimal representation, but in reverse order
    unit, p = resolve_precision(precision)

    assert base_unit in 'hms'
    assert unit in 'hms'
    v = 'smh'.index(base_unit)
    w = 'smh'.index(unit)
    assert v >= w, 'Base unit must be greater than precision unit.'

    # compute parts and round
    s = [1, -1][int(t < 0)]
    t = abs(t) / 60 ** w
    for _ in range(v - w):
        t, r = divmod(t, 60)
        if p is not None:
            q, r = divmod(round(r, p), 60)
            t += q
            p = None  # only round tail unit
        yield s * r
    yield s * t


class YMDHMS:

    def __init__(self, sep=None, ascii=False,
                 fill=('', '', '', '0', '0', '0'),
                 width=('', '', '', 2, 2, 2)):
        
        self.sep = tuple(self._resolve_sep(sep, ascii))
        
        assert len(fill) == len(width) == 6
        self.fill = fill
        self.width = width

    def __call__(self, t, base_unit=None, spec='s9?') -> str:
        return ''.join(self._iter(t, *self._parse_spec(t, base_unit, spec))).rstrip()

    def _iter(self, t, u, v, p, short):
        # compute parts and round
        if t < 0:
            yield ('-' if ascii else '\N{MINUS SIGN}')

        #
        r = abs(t)
        sep = itt.islice(iter(self.sep), u, v + 1)
        for d, f, w in itt.islice(zip(TIME_DIVISORS, self.fill, self.width), u, v):
            t, r = divmod(r, d)
            yield f'{int(t):{f}{w}d}'
            yield next(sep, '')

        r /= TIME_DIVISORS[v]

        if w := self.width[v]:
            w += int(p)

        s = f'{r:{self.fill[v]}{w}.{p}f}'

        if short and p:
            s = s.rstrip('0').rstrip('.')

        yield s
        yield from sep

    def _parse_spec(self, t, base_unit, spec):
        # parse spec
        mo = REGEX_YMDHMS_SPEC.match(spec)

        mag = 'yMdhms'
        v = mag.index(base_unit) if base_unit else op.index(TIME_DIVISORS, t, test=op.le)
        w = mag.index(mo['tail_unit'])
        if v > w:
            raise ValueError(f'Base unit ({mag[v]!r}) must have greater magnitude '
                             f'than tail unit ({mag[w]!r}).')
        return v, w, (mo['precision'] or 0), bool(mo['short'])

    def _resolve_sep(self, sep, ascii):
        if sep is None:
            return (YMDHMS_ASCII if ascii else YMDHMS_SUPER)

        nsep = len(sep)
        if nsep in {0, 1}:
            return itt.repeat(sep, 5)

        assert nsep in {5, 6}
        return sep


def ymdhms(t, base_unit=None, spec='s9?', sep=None, ascii=False, **kws):
    return YMDHMS(sep, ascii)(t, base_unit, spec)


# class ydmhms:
#     sep = 'yMdhms'
#     fill = ('', '', '', '0', '0', '0')
#     width = ('', '', '', 2, 2, 2)

#     def __init__(self, t, base_unit=None, spec='s9?', ascii=False, sep=sep):

#         nsep = len(sep)
#         assert nsep in {0, 1, 6}
#         if nsep in {0, 1}:
#             sep = [sep] * 6
#         elif not ascii:
#             sep = SUPERSCRIPTS

#         # parse spec
#         mo = REGEX_YMDHMS_SPEC.match(spec)
#         kws = mo.groupdict()
#         self.__dict__.update(kws)
#         # tail_unit, precision, short

#         self.parts = list(_ydmhms(t, sep=sep, **kws))
#         # short = is_hms if short is None else short
#         # short representation only meaningful if time expressed with hms separator.
#         # ie. the separators express magnitude, unlike using ":"

#     # def __format__(self, spec='s9?'):

#     def __str__(self):

#         # start = self.sep.index(next(iter(self.parts.keys())))
#         sep, val = self.parts[:-1]

#         itr = mit.islice(zip(self.fill, self.width), start, stop)

#         for sep, val in self.parts.items():
#             unit =
#             f'{val:<{f}{w}g}{unit}'
#             # f'{val:<{f}{w}.{p}f}{unit}'

#         # for mag, val in self.parts.items():

#         # for unit, val in parts:
#         #     f'{val:<{fill}{width}.{p}f}{unit}'


# def _to_ymdhms(t, ):

# class _ydmhms:
#     __slots__ = [*'yMdhms', 't', '_v', '_w']

#     def __init__(self, t, base_unit=None, tail_unit='s'):
#         # generator that computes ydmhms representation
#         self.t = t
#         mag = self.__slots__[:6]
#         self._v = v = (mag.index(base_unit) if base_unit else
#                        op.index(TIME_DIVISORS, t, test=op.le))
#         self._w = w = mag.index(tail_unit)
#         # print(v, w)
#         assert v < w, 'Base unit must have greater magnitude than precision unit.'

#         # compute parts and round
#         s = [1, -1][int(t < 0)]
#         r = t
#         for i in range(v, w):  # for d in TIME_DIVISORS[v:w]:
#             d = TIME_DIVISORS[i]
#             # print(r, d)
#             t, r = divmod(r, d)
#             setattr(self, self.__slots__[i], s * int(t))

#         r /= TIME_DIVISORS[w]
#         yield setattr(self, self.__slots__[i], s * round(r, p))

#     def __format__(self, spec='h^s9?'):
#         # parse spec
#         mo = REGEX_YMDHMS_SPEC.match(spec)
#         kws = mo.groupdict()
#         for part in self.__slots__[self._v:self._w - 1]:
#             sep = getattr(self, part)


# @ doc.splice(to_sexagesimal)
def resolve_precision(precision):
    """
    Resolve the unit and number of significant digits for a precision specifier
    a sexagesimal number

    Parameters
    ----------
    precision : int or str or None
        {Parameters[precision].desc}

    Returns
    -------
    str, int
        unit, significant digits

    Raises
    ------
    ValueError
        If invalid specifier
    """
    if isinstance(precision, int):
        return 's', precision

    if isinstance(precision, str):
        if mo := REGEX_YMDHMS_PRECISION.fullmatch(precision):
            unit, precision = mo.groups()
            precision = int(precision) if precision else None
            return unit, precision

    raise ValueError(f'Invalid precision specifier {precision!r}')


# @ doc.splice(to_sexagesimal)
def hms(t, precision=None, sep='hms', base_unit='h', short=False, unicode=False):
    """
    Create sexagesimal time representation string from input float seconds.

    This function can abe used get the representation of an input time in base
    units of minutes or hours (by specifying `base_unit`), and with unit
    precision of seconds or minutes, and numerical precision of any number 0-9.


    Parameters
    ----------
    {Parameters[t]}
    {Parameters[precision]}
        Note that providing precision as an int, while also specifying
        short=True does not gaurantee that the number will be given with all the
        decimal digits filled since superfluous trailing 0s will be stripped.
    sep: str
        Separator(s) to use for time representation.
    {Parameters[base_unit]}
    short: bool or None
        Will strip unnecessary parts from the repr if True.
        eg: '0h00m15.4000s' becomes '15.4s'
    unicode: bool
        Use unicode superscripts (ʰᵐˢ) as separators.

    Returns
    -------
    formatted time str

    Examples
    --------
    >>> hms(1e4)
    '2h46m40s'
    >>> hms(1.333121112e2, 5)
    '2m13.31211s'
    >>> hms(1.333121112e2, 5, ':')
    '0:02:13.31211'
    >>> hms(1.333121112e2, 5, short=False)
    '0h02m13.31211s'
    >>> hms(1.333121112e2, 0, unicode=True)
    """

    nsep = len(sep)
    assert nsep in {0, 1, 3}
    repeat_sep = (nsep in {0, 1})
    is_hms = (sep == 'hms')
    short = is_hms if short is None else short
    # short representation only meaningful if time expressed with hms separator.
    # ie. the separators express magnitude, unlike using ":"

    # resolve separator
    if unicode and is_hms:
        sep = YMDHMS_SUPER[3:]  # 'ʰᵐˢ'
    elif repeat_sep:
        base_unit = 'h'  #

    # resolve precision
    sexa = to_sexagesimal(t, base_unit, precision or 's')
    m = len(sexa) - 1
    if precision is None:
        unit = 's'
    else:
        unit, precision = resolve_precision(precision)
    precision = [0] * m + [precision]

    # get separators
    if repeat_sep:
        sep = [sep] * m + ['']
    else:
        sep = sep['hms'.index(base_unit):('hms'.index(unit) + 1)]

    out = ''
    fun = echo0
    for n, p, s in zip(sexa, precision, sep):
        if short and not n:
            continue
        short = False  # only first number can be truncated

        out += pad(decimal(fun(n), p, unicode=unicode), left=(2, '0')) + s
        fun = abs

    return out

#
# def ymdhms(t):


def eng(value, significant=None, base=10, unit=''):
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
    sign = signum(value)
    value = np.abs(value)
    if sign == 0:
        return str(value)

    pwr = np.log(value) / np.log(base)
    pwr3 = int((pwr // 3) * 3)
    prefix = METRIC_PREFIXES[pwr3]

    size = value / (base ** pwr3)
    if significant is None:
        significant = [0, 1][pwr3 < 0]
    return '{:.{:d}f}{}'.format(size, significant, f' {prefix}{unit}')


engineering = eng

# TODO: docstring / API consistency


def decimal(n, precision=None, significant=3, sign='-', short=False,
            unicode=False, thousands=''):
    """
    Decimal representation of float as str up to given number of significant
    digits (relative), or decimal precision (absolute). Support for
    minimalist `short` representations as well as optional left- and right
    padding and unicode representation of minus/infinity (−/∞) included.

    Parameters
    ----------
    n: numbers.Real
        The number to be formatted.
    precision: int, optional
        if int:
            decimal precision (absolute) for format.
        if None:
            precision = 1 if the abs(number) is larger than 1. eg. 100.1
            Otherwise it is chosen such that at least 3 significant digits are
            shown: eg: 0.0000345 or 0.985
    significant: int, optional
        If precision is not given, this gives the number of non-zero digits
        after the decimal point that will be displayed. This argument allows
        specification of dynamic precision values.
    sign: str or bool, optional
        True: always sign; False: only negative
        '+' or '-' or ' ' behaves like builtin format spec
    short : bool, optional
        If True, redundant zeros after decimal point will be stripped to yield a
        more compact representation of the same number.
    unicode:
        # TODO: latex:\\infty also spaces for thousands also ignore padding ???
        prefer unicode minus '−' over '-'
        prefer unicode infinity '∞' over 'inf'

    thousands: str
        thousands separator


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
    # # handel masked values
    # if isinstance(n, np.ma.core.MaskedConstant):
    #     return '--'

    # ensure we have a scalar
    if not isinstance(n, numbers.Real):
        raise ValueError('Only scalars are accepted by this function.')

    # handle nans
    if np.isnan(n):
        return 'nan'

    # get sign
    if sign is None:
        sign = '-'
    if isinstance(sign, bool):
        sign = '-+'[sign]
    if not isinstance(sign, str) or sign not in ' -+':
        raise ValueError(
            f'Invalid sign {sign!r}. Use one of "+", "-", " ". Set '
            f'`unicode=True` if you want a unicode minus.')
    sign_fmt = sign

    # automatically decide on a precision value if not given
    m = None
    if (precision is None):  # or (left_pad > 0) or (right_pad > 0):
        # order of magnitude and `significant` determines precision
        m = order_of_magnitude(n)
        if np.isinf(m):
            m = 0

    # print('oom',m)
    # if precision is None:
        precision = int(significant) - min(m, 1) - 1

    precision = max(precision, 0)
    # TODO: precision < 0 do rounding

    # format the number
    _1000fmt = ',' if thousands else ''
    s = f'{n:{sign_fmt}{_1000fmt}.{precision}f}'.replace(',', thousands)

    if unicode:
        s = s.replace('inf', '\N{INFINITY}')

    # strip redundant zeros
    # n_stripped = 0
    # width = len(s)
    if precision > 0 and short:
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

    if unicode:
        s = s.replace('-', '\N{MINUS SIGN}')
    return s


def pad(s, left=None, right=None):
    # # TODO: replace with    pad=(5, 7)
    #                         pad=dict(l=5, r=7)
    #                         pad=[(5, '0'), 7]
    #                         pad='<5'
    # left_pad: int, tuple
    #     width of the portion of the number preceding the decimal point.  If
    #     number string is shorter than `left_pad`, whitespace will be pre-padded.
    #     eg.:
    #         '1.23301' ---> ' 1.23301' (with left_pad=2)
    #     This option is useful when displaying numbers in a column and having
    #     them all line up nicely with the decimal points.
    # right_pad: int
    #     width of the portion of the number following the decimal point.
    #     Trailing whitespace padding relative to decimal point.
    #     eg.:
    #         '1.233' ---> ' 1.233  ' (with right_pad=6)

    # pad relative to decimal position

    # left = _check_pad(left)
    # right = _check_pad(right)

    # pad with whitespace relative to decimal position. useful when displaying
    # arrays of decimal numbers.
    # Left pad used and we need to line up with decimal position of larger
    # numbers.
    # if left_pad > 0:  # need this to know if m is in namespace!!!
    #     if left_pad > min(m, 0):
    #         # total display width
    #         w = left_pad + precision + int(precision > 0)
    #         #                        ⤷ +1 if number has decimal point
    #         s = s.rjust(w, left_pad_char)

    #     if isinstance(lr, numbers.Integral):
    #         lr = (lr, ' ')  # pad space

    pre, *post = s.partition('.')
    post = ''.join(post)
    return ''.join((pre.rjust(*_check_pad(left or len(pre))),
                    post.ljust(*_check_pad(right or len(post)))))

#     return ''.join((left_pad(pre, *left),
#                     right_pad((post, *right)))

# def left_pad(s, width, char=' '):
#     return s.rjust(width or len(s), char)

# def right_pad(s, width, char=' '):
#     return s.ljust(width or len(s), char)


def align_dot(data):
    int_, dot, dec = np.char.partition(np.array(data, 'U'), '.').T
    tail = list(map(''.join, zip(dot, dec)))
    # w0 = max(map(len, i))
    # w1 = max(map(len, tail))
    return list(map(''.join, zip(np.char.rjust(int_, max(map(len, int_))),
                                 np.char.ljust(tail, max(map(len, tail))))))


def decimal_with_percentage(n, total, precision=None, significant=3, sign='-',
                            short=False, unicode=False, thousands='',
                            brackets='()'):

    p0, p1 = duplicate_if_scalar(precision, 2)

    return ' '.join(
        (decimal(n, p0, significant, sign, short, unicode, thousands),
         f'{n / total:.{p1}%}'.join(brackets))
    )


class Notation:
    pass


def resolve_sign(sign):
    # get sign
    if sign is None:
        return '-'

    if isinstance(sign, bool):
        return '-+'[sign]

    if (isinstance(sign, str) and (sign in ' -+')):
        return sign

    raise ValueError(f'Invalid sign {sign!r}. Use one of "+", "-", " ". Set '
                     f'`unicode=True` if you want a unicode minus.')


class Decimal(Notation):
    def __init__(self, n):

        # ensure we have a scalar
        if not isinstance(n, numbers.Real):
            raise ValueError('Only scalars are accepted by this function.')

        self.n = float(n)

    def __call__(self,  precision=None, significant=5, sign=False, short=False,
                 thousands='', style='ascii'):

        return self.format(precision, significant, sign, short, thousands, style)

    def format(self,  precision=None, significant=5, sign=False, short=False,
               thousands='', style='ascii'):

        if np.isnan(self.n):
            return 'nan'

        if np.isinf(self.n):
            return INFINITY_SYMBOLS[style]

        sign_fmt = resolve_sign(sign)

        # automatically decide on a precision value if not given
        m = None
        if (precision is None):  # or (left_pad > 0) or (right_pad > 0):
            # order of magnitude and `significant` determines precision
            m = order_of_magnitude(self.n)
            if np.isinf(m):
                m = 0

            precision = int(significant) - min(m, 1) - 1

        precision = max(precision, 0)
        # TODO: precision < 0 do rounding

        # format the number
        _1000fmt = ',' if thousands else ''
        s = f'{self.n:{sign_fmt}{_1000fmt}.{precision}f}'.replace(',', thousands)

        # strip redundant zeros
        # n_stripped = 0
        # width = len(s)
        if precision > 0 and short:
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

        if style == 'unicode':
            return s.replace('-', '\N{MINUS SIGN}')
        return s


class Sci:
    """
    Represent a number in scientific notation in various styles.
    """

    def __init__(self, n):

        # ensure we have a scalar
        if not isinstance(n, numbers.Real):
            raise ValueError('Only scalars are accepted by this function.')

        self.n = float(n)
        self.m = m = order_of_magnitude(self.n)  # might be -inf
        self.v = n * (10 ** -m)  # coefficient / mantissa / significand as float

    def __call__(self, significant=5, sign=False, times='x', short=False,
                 style='ascii'):

        return self.format(significant, sign, times, short, style)

    def format(self, significant=5, sign=False, times='x', short=False,
               style='ascii'):
        """
        Format the number in scientific notation.

        Parameters
        ----------
        significant : int, optional
            [description], by default 5
        sign : bool, optional
            [description], by default False
        times : str, optional
            [description], by default 'x'
        short : bool, optional
            [description], by default False
        style : str, optional
            [description], by default 'ascii'

        Examples
        --------
        >>> 

        Returns
        -------
        [type]
            [description]
        """
        if np.isnan(self.n):
            return 'nan'

        if np.isinf(self.n):
            return INFINITY_SYMBOLS[style]

        # first get the ×10ⁿ part
        times, base, exp = self.get_parts(style, times)

        # mantissa string
        mantis = decimal(self.v, None, significant, sign, short,
                         style == 'unicode')

        if short and self.m > 0 and mantis == '1':
            mantis = times = ''

        # concatenate
        r = ''.join([mantis, times, base, exp])

        if style == 'latex':
            return f'${r}$'
            # TODO: make this wrap optional. since decimal does not do this
            #  integration within numeric is bad

        return r

    def get_parts(self, style, times):
        m = self.m
        if m == 0:
            return '', '', ''

        if times.lower() == 'e':
            # implies style == 'ascii'
            return '', times, str(m)

        base = '10'
        if style == 'unicode':
            times = PRODUCT_SYMBOLS.get(times, times)
            pwr_sgn = ['', '\N{SUPERSCRIPT MINUS}'][m < 0]
            exp = pwr_sgn + uni.superscript.translate(abs(m))
            return times, base, exp

        exp = '' if m == 1 else str(m)
        if style == 'ascii':
            return times, base, exp

        # latex
        times = PRODUCT_SYMBOLS_LATEX.get(times, times)
        return times, base, f'^{exp}'

    def ascii(self, significant=5, sign=False, times='x', short=False):
        return self.format(significant, sign, times, short, 'ascii')

    def latex(self, significant=5, sign=False, times='x', short=False):
        return self.format(significant, sign, times, short, 'latex')

    def unicode(self, significant=5, sign=False, times='x', short=False):
        return self.format(significant, sign, times, short, 'unicode')


def sci(n, significant=5, sign=False, times='x',  # x10='x' ?
        short=False, unicode=None, latex=None, eng=False):
    # todo: format='latex' / unicode / engineering
    """
    Scientific numeral representation strings in various formats.
    See:  https://en.wikipedia.org/wiki/Scientific_notation

    Parameters
    ----------
    n: scalar
        The number to be represented
    significant: int
        Number of significant figures to display.
    sign: str, bool
        add '+' to positive numbers if True.
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
    short: bool
        If True, redundant zeros after decimal point will be stripped to yield a
        more compact representation of the same number.
    unicode: bool
        prefer unicode minus symbol '−' over '-'
        prefer unicode infinity symbol  '∞' over 'inf'
        prefer unicode multiplication symbol '×' over 'x'
    latex:
        represent the number as a latex string:
        eg:. '$1.04 \\times 10^{-12}$'
    engineering: bool
        Prefer representation where exponent is a multiple of 3. Essentially
        scientific notation with base 1000.


    # TODO: spacing options.  # ' x ' as times :)
    # todo: SI prefixes

    Returns
    -------
    str
    """

    # ensure we have a scalar
    if not isinstance(n, numbers.Real):
        raise ValueError('Only scalars are accepted by this function.')

    # handle nans
    if np.isnan(n):
        return 'nan'

    # check flags
    if (unicode, latex) == (None, None):
        unicode = True  # default is to prefer unicode
    assert not (unicode and latex)  # can't do both!

    #
    # n_ = abs(n)
    m = order_of_magnitude(n)  # might be -inf

    # scientific notation
    # first get the ×10ⁿ part
    if m == 0:
        times, base, exp = '', '', ''
    else:
        base = '10'
        if times.lower() == 'e':
            base = times  # e or E
            times = ''
            unicode = False

        if unicode:
            times = PRODUCT_SYMBOLS.get(times, times)
            pwr_sgn = ['', '\N{SUPERSCRIPT MINUS}'][m < 0]
            exp = pwr_sgn + uni.superscript.translate(abs(m))
        else:
            pwrFmt = '%i'
            if latex:
                pwrFmt = '^{%i}'
                times = PRODUCT_SYMBOLS_LATEX.get(times, times)
            exp = '' if m == 1 else pwrFmt % m

    # if short:
    #     # short representation of number eg.: 10000  ---> 1e5  or 10⁵
    #     raise NotImplementedError

    # finally bring it all together
    v = n * (10 ** -m)  # coefficient / mantissa / significand as float
    # mantissa as str
    mantis = decimal(v, None, significant, sign, short, unicode)

    # mantis = formatter(v)
    if mantis == '1' and m > 0 and short:
        mantis = times = ''

    # concatenate
    r = ''.join([mantis, times, base, exp])

    if latex:
        return f'${r}$'
        # TODO: make this wrap optional. since decimal does not do this
        #  integration within numeric is bad

    return r


def numeric(n, precision=3, significant=3, log_switch=5, sign='-', times='x',
            short=True, thousands='', unicode=None, latex=None,
            engineering=False):
    """

    Parameters
    ----------
    significant
    n
    precision
    log_switch: int # TODO: tuple  
        Controls switching between decimal/scientific notation. Scientific
        notation is triggered if `abs(math.log10(abs(n))) > log_switch`.

    short
        TODO: If short = True
        Default is chosen in such a way that the representation of the number
        is as short as possible. eg: '1.01445 × 10²' can be more shortly
        represented as '101.445'; 1000 can be more shortly represented as
        10³ or 1K depending on your tastes or needs.
    times
    sign
    unicode
    latex
    engineering
    thousands

    Returns
    -------

    """
    # ensure we have a scalar
    if not isinstance(n, numbers.Real):
        # TODO: dispatch on int, float, complex, array
        try:
            n = float(n)
        except ValueError as err:
            raise ValueError('Only scalars are accepted by this function.') \
                from err

    # check special behaviour flags
    assert not (unicode and latex)  # can't do both!

    # n_ = abs(n)
    m = order_of_magnitude(n)  # might be -inf

    # if short:
    #     formatter = partial(decimal, precision=precision)
    # else:
    #     formatter = ('{:.%if}' % precision).format

    if log_switch is False:
        # always display decimal format
        log_switch = math.inf
    if log_switch is True:
        # always display log format
        log_switch = 0
    if log_switch is None:
        # decide format based on precision
        log_switch = precision
    # TODO lower and upper switch...

    # m = order_of_magnitude(n)
    if math.isinf(m) or abs(m) < log_switch:
        # handle case n == 0 and normal float formatting
        return decimal(n, precision, None, sign, short, unicode,
                       thousands=thousands)

    return sci(n, significant, sign, times, short, unicode, latex,
               engineering)


nr = number = numeric


def numeric_array(n, precision=2, significant=3, log_switch=5, sign=' ',
                  times='x', short=False, unicode=None, latex=None,
                  engineering=False, thousands=''):
    """Pretty numeric representations for arrays of scalars"""
    # note default args slightly different:
    #   sign ' ' instead of '-'  for alignment
    return vectorize(numeric)(**locals())


# ------------------------------------------------------------------------------
# Uncertainties:
# ------------------------------------------------------------------------------

# TODO: precision_rules: 'uipac', 'uipap' ??
def precision_rule_dpg(u):
    # Data Particle Group rules
    # http://pdg.lbl.gov/2010/reviews/rpp2010-rev-rpp-intro.pdf (section 5.4:
    #  Rounding, pg 13)

    # "" The basic rule states that if the three highest order digits of the
    # error [sic] lie between 100 and 354, we round to two significant digits.
    # If they lie between 355 and 949, we round to one significant digit.
    # Finally, if they lie between 950 and 999, we round up to 1000 and keep two
    # significant digits. In all cases, the central value is given with a
    # precision that matches that of the error [sic]. So, for example, the
    # result (coming from an average) 0.827 ± 0.119 would appear as 0.83 ± 0.12,
    # while 0.827 ± 0.367 would turn into 0.8 ± 0.4. ""

    nrs, m = get_significant_digits(u, 3)
    #
    if 100 <= nrs < 355:
        r = 1  # round to two significant digits
    elif 355 < nrs < 950:
        r = 0  # round to one significant digit
    else:
        r = -1  # round up to 1000 and keep two significant digits
    return r - m  # precision


# def n_sig_dpg(u):
#
#     nrs, m = get_significant_digits(u, 3)
#     #
#     if 100 <= nrs < 355:
#         r = 1  # round to two significant digits
#     elif 355 < nrs < 950:
#         r = 0  # round to one significant digit
#     else:
#         r = -1  # round up to 1000 and keep two significant digits
#     return -m + r  # precision


def decimal_u(x, u, precision=None, short=False,
              sign=False, thousands='', unicode=True, latex=False):
    """
    Represent a number with associated standard deviation uncertainty as str.


    Parameters
    ----------
    x
    u
    precision
    short
    sign
    unicode
    latex

    Returns
    -------

    """
    if u is None or u is False or not np.isfinite(u):
        return decimal(x, precision, 0, sign, short, thousands=thousands)

    if precision is None:
        precision = precision_rule_dpg(u)
    precision = int(precision)  # type enforcement

    xr = decimal(x, precision, 0, sign, short, thousands=thousands)
    ur = decimal(u, precision, 0, '', short, thousands=thousands)

    if unicode:
        return f'{xr} ± {ur}'

    if latex:
        return Rf'${xr} \pm {ur}$'

    return f'{xr} +/- {ur}'


# def vectorize():
#     # handle masked arrays
#     if np.ma.is_masked(xr):
#         xr = np.ma.filled(xr, str(np.ma.masked))


def uarray(x, u, significant=None, log_switch=5, short=False, times='x',
           sign='-', thousands='', unicode=True, latex=False, engineering=False):
    """

    Parameters
    ----------
    x
    u
    precision
    short:
        default False since shortly represented numbers in arrays will be
        relatively mis-aligned.
    times
    sign
    unicode
    latex
    engineering

    Returns
    -------

    """
    # Note: numpy offers no way of formatting arrays where the formatting is
    #  decided based on the number of array elements that will be displayed.
    #  this needs a PR!!!

    # TODO:
    #  max_line_width=None, precision=None,
    #  suppress_small=None, separator=' ', prefix="",
    #  style=np._NoValue, formatter=None, threshold=None,
    #  edgeitems=None, sign=None, floatmode=None, suffix=""

    # It's important here to line up the various parts of the representation
    # so that the numbers can easily be compared scrolling your eye along a
    # column. We also might want uniform magnitude scaling across the array.

    # TODO: first decide which items to display.  get_edge_items etc...

    if np.size(x) > 1000:
        #
        raise NotImplementedError('Probably not a good idea. Not yet tested for'
                                  '  large arrays.')

    # check uncertainty ok
    if u is None or u is False or np.isnan(u).all():
        warnings.warn('Ignoring invalid uncertainty array.')
        del u
        kws = locals()
        return numeric_array(kws.pop('x'), **kws)

    # decide on scientific vs decimal notation
    oom = np.floor(np.round(np.log10(abs(x)), 9)).astype(int)
    mmin, mmax = oom.min(), oom.max()
    mag_rng = mmax - mmin  # dynamic range in order of magnitude
    if mag_rng > log_switch:
        raise NotImplementedError('use sci for entire array')

    if significant is None:
        # get precision values from the Data Particle Group rules
        precision = vectorize(precision_rule_dpg)(u[np.isfinite(u)]).max()
    else:
        precision = significant

    # get plus-minus character
    # if unicode:
    #     pm = UNI_PM
    # elif latex:
    #     pm = '\pm'
    # else:
    #     pm = '+-'
    # # spacing
    # pm = ' %s ' % pm

    # here we can either display all digits for all elements up to
    # `significant` or we can fill trailing whitespace up to `significant`.

    # option 1
    return vectorize(decimal_u)(x, u, precision=precision,
                                short=short, sign=sign, thousands=thousands,
                                unicode=unicode, latex=latex)

    # return xr

    # option 2

    # return xr

    # σ = unp.std_devs(a)
    # return list(map(leading_decimal_zeros, σ))


def sci_array(n, significant=5, sign='-', times='x',  # x10='x' ?
              short=False, unicode=None, latex=None, engineering=False):
    """Scientific representation for arrays of scalars"""
    # masked data handled implicitly by vectorize
    # from recipes.array.misc import vectorize

    return vectorize(sci)(**locals())


def matrix(a, precision=3):
    """
    A nice matrix representation of an array:
    Eg:
        ┌                  ┐
        │     0.939  0.216 │
        │    -0.001  0     │
        │   -65.233  0     │
        │  -845.044  0     │
        │ -3111.366  0     │
        └                  ┘

    Parameters
    ----------
    a
    precision

    Returns
    -------

    """

    # UPPER_LEFT = u'\u250c'        ┌
    # UPPER_RIGHT = u'\u2510'       ┐
    # LOWER_LEFT = u'\u2514'        └
    # LOWER_RIGHT = u'\u2518'       ┘
    # HORIZONTAL = u'\u2500'
    # VERTICAL = u'\u2502'          │

    from motley.table import Table
    from motley.utils import hstack

    tbl = Table(a, precision=precision, frame=False, col_borders=' ',
                minimalist=True, title='', title_style={})
    n_rows, _ = tbl.data.shape
    left = '\n'.join('┌' + ('│' * n_rows) + '└')
    right = '\n'.join([' ┐'] + [' │'] * n_rows + [' ┘'])
    return hstack([left, tbl, right])


# def matrix(a, precision=2, significant=3, log_switch=5, sign=' ', times='x',
#           short=False, unicode=True, latex=False, engineering=False,
#           thousands=''):
#     """"""
#     q = numeric_array(a, precision, significant, log_switch, sign, times, short,
#                       unicode, latex, engineering, thousands)
#
#     return _matrix_repr(q)


#
class PrettyPrinter(pprint.PrettyPrinter):
    """Hack the PrettyPrinter for custom handling of float, int and str types"""

    def __init__(self, indent=1, width=80, depth=None, stream=None, *,
                 compact=False, precision=None, minimalist=True):

        if minimalist:
            self._floatFormatFunc = decimal
        else:
            self._floatFormatFunc = '{:.{}f}'.format
            precision = precision or 3

        self.precision = precision
        self.minimalist = minimalist

        super().__init__(indent, width, depth, stream, compact=compact)

    def pformat(self, obj):
        """
        Format object for a specific context, returning a string
        and flags indicating whether the representation is 'readable'
        and whether the object represents a recursive construct.
        """
        # intercept float formatting
        if isinstance(obj, numbers.Real):
            return self._floatFormatFunc(obj, self.precision,
                                         short=self.minimalist)

        # for str, return the str instead of its repr
        if isinstance(obj, str):
            return obj

        # TODO: figure out how to do recursively for array_like
        return pprint.PrettyPrinter.pformat(self, obj)
