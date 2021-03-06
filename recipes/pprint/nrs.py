"""
Pretty formatting of floats, arrays (with uncertainties) in various human
readable forms
"""

# This module designed for convenience and is *not* speed tested (yet)

# std libs
import math, re
import pprint
import numbers
from collections import namedtuple

# third-party libs
import numpy as np

# local libs
from recipes.array.misc import vectorize

# note: unicode literals below python3 only!
# see: https://docs.python.org/3/howto/unicode.html


HMS = namedtuple('HMS', list('hms'))

# Unicode
UNI_PWR = dict(enumerate('²³⁴⁵⁶⁷⁸⁹', 2))  # '¹²³⁴⁵⁶⁷⁸⁹'
UNI_NEG_PWR = '⁻'  # '\N{SUPERSCRIPT MINUS}'
UNI_PM = '±'
UNI_MULT = {'x': '×', '.': '·'}
UNI_HMS = u'ʰᵐˢ'
# '\N{MINUS SIGN}'              '−'     u'\u2212'
# '\N{PLUS-MINUS SIGN}'         '±'
# '\N{MULTIPLICATION SIGN}'     '×' 	u'\u00D7'
# '\N{MIDDLE DOT}'              '·'     u'\u00B7'
# '\N{INFINITY}                 '∞'     u'\u221E'
# convert unicode to hex-16: '%x' % ord('⁻')

# LaTeX
LATEX_MULT = {'x': r'\times', '.': r'\cdot'}

# The SI metric prefixes
METRIC_PREFIXES = {-24: 'y',
                   -21: 'z',
                   -18: 'a',
                   -15: 'f',
                   -12: 'p',
                   -9: 'n',
                   -6: 'µ',
                   -3: 'm',
                   0: '',
                   3: 'k',
                   6: 'M',
                   9: 'G',
                   12: 'T',
                   15: 'P',
                   18: 'E',
                   21: 'Z',
                   24: 'Y'}

sequences = (list, tuple)


#  centi-, deci-, deka-, and hecto-) ???

# Regex matchers for decimal and scientific notation
# SCI_SRE = re.compile('[+-]?\d\.?\d?e[+-]?(\d\d)', re.ASCII)
# DECIMAL_SRE = re.compile('[+-]?\d+\.(0*)[1-9][\d]?', re.ASCII)


def signum(n):
    if n == 0:
        return 0
    if n < 0:
        return -1
    return 1


def order_of_magnitude(n, base=10):
    """
    Order of magnitude for a scalar.

    Parameters
    ----------
    n: any python scalar
    base: int

    Returns
    -------

    """
    if not isinstance(n, numbers.Real):
        raise ValueError('Only scalars are accepted by this function.')

    if n == 0:
        return -math.inf

    logn = math.log(abs(n), base)
    # note that the rounding error on log calculation is such that `logn`
    # may be slightly less than the correct theoretical answer. Eg:
    # log(1e12, 10) gives 11.999999999999998.  We need to round to get the
    # correct order of magnitude.
    return math.floor(round(logn, 9))  # returns an int


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
    if m > 0 or math.isinf(m):
        return 0
    else:
        return -m - 1


def get_significant_digits(x, n=3):
    """
    Return the first `n` non-zero significant digits

    Parameters
    ----------
    x: any python scalar
    n: int
        number of significant digits to return

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
    result in a 3-tuple with floats for (hours, minutes, seconds).  If the
    time is desired in units of (minutes, seconds), pass `base_unit='m'`.
    Using `base_unit='s'` will simply wrap the input number in a list.

    Parameters
    ----------
    t: float
        time in seconds
    base_unit

    Returns
    -------
    namedtuple
    """
    assert base_unit in 'hms'
    assert precision in 'hms'

    v = 'smh'.index(base_unit)
    w = 'smh'.index(precision)
    assert v >= w

    #
    t = t / 60 ** w
    q = []
    for i in range(v - w):
        t, r = divmod(t, 60)
        q.append(r)
    q.append(t)
    return tuple(q[::-1])

    # m, s = divmod(t, 60)
    # h, m = divmod(m, 60)
    # return HMS(h, m, s)


# def zeroth(x):
#     return x[0]

REGEX_HMS_PRECISION = re.compile('([hms])\.?(\d)?')


def hms(t, precision=None, sep='hms', base_unit='h', short=False,
        unicode=False):
    """
    Convert time in seconds to sexagesimal representation

    Parameters
    ----------
    t : float
        time in seconds
    precision: int or str or None
        maximum precision to use. Will be ignored if a shorter numerical
        representation exists and short=True
    sep: str
        separator(s) to use for time representation
    base_unit: str {'h', 'm', 's'}
        The largest unit for the resulting representation. For example, if
        the result is desired in units of (minutes, seconds), use
        `base_unit='m'`.
    short: bool or None
        will strip unnecessary parts from the repr if True.
        eg: '0h00m15.4s' becomes '15.4s'
    unicode: bool
        Unicode superscripts

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
    """

    # TODO: unit tests!!!

    if len(sep) == 1:
        sep = (sep, sep, '')
        base_unit = 'h'  #

    if short is None:
        # short representation only meaningful if time expressed in hms units
        short = (sep == 'hms')

    if unicode and (sep == 'hms'):
        sep = UNI_HMS

    # resolve precision
    hms_precision = 's'
    if isinstance(precision, str):
        mo = REGEX_HMS_PRECISION.fullmatch(precision)
        if mo:
            hms_precision, precision = mo.groups()
            precision = int(precision or 0)
        else:
            raise ValueError('Invalid precision key %r' % precision)

    #
    sexa = to_sexagesimal(t, base_unit, hms_precision)
    precision = [0] * (len(sexa) - 1) + [precision]

    parts = []
    for i, (n, p, s) in enumerate(zip(sexa, precision, sep)):
        if short and not n:
            continue
        else:
            short = False

        parts.append(decimal(n, p, left_pad=(2, '0'),
                             unicode=unicode) + s)
    return ''.join(parts)

    # stop = 2
    # if short:
    #     for i, x in enumerate(sexa[::-1]):
    #         if x:
    #             break
    #     stop = 2 - i
    #
    # #
    # tstr = ''
    # for i, (n, p, s) in enumerate(zip(sexa, precision, sep)):
    #     # if this is the first non-zero part, skip zfill
    #     part = decimal(n, p,
    #                    left_pad=(2 * bool(len(tstr)), '0'),
    #                    unicode=unicode)
    #     tstr += (part + s)
    #     if i == stop:
    #         break
    #
    # return tstr


# alias
sexagesimal = hms
sexagesimal.__doc__ = hms.__doc__.replace('hms', 'sexagesimal')


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


# TODO: docstring / API consistencey
def decimal(n, precision=None, significant=3, sign='-', compact=False,
            unicode=False, left_pad=0, right_pad=0, thousands=''):
    """
    Decimal representation of float as str up to given number of significant
    digits (relative), or decimal precision (absolute). Support for
    minimalist `compact` representations as well as optional left- and right
    padding and unicode representation of infinity '∞' included.

    Parameters
    ----------
    n: int or float
        the number to format
    precision: int, optional
        if int:
            decimal precision (absolute) for format.
        if None:
            precision = 1 if the abs(number) is larger than 1. eg. 100.1
            Otherwise it is chosen such that at least 3 significant digits are
            shown: eg: 0.0000345 or 0.985
    significant: int
        If precision is not given, this gives the number of non-zero digits
        after the decimal point that will be displayed. This argument allows
        specification of dynamic precision values.
    sign: str or bool
        True: always sign; False: only negative
        '+' or '-' or ' ' behaves like builtin format spec
    compact : bool  # TODO: terse ??
        if True, redundant zeros and decimal point will be stripped.
    unicode:
        # TODO: latex: \infty also spaces for thousands also ignore padding ???
        prefer unicode minus '−' over '-'
        prefer unicode infinity '∞' over 'inf'
    # TODO: replace with    pad=(5, 7)
                            pad=dict(l=5, r=7)
                            pad=[(5, '0'), 7]
                            pad='<5'
    left_pad: int, tuple
        width of the portion of the number preceding the decimal point.  If
        number string is shorter than `left_pad`, whitespace will be pre-padded.
        eg.:
            '1.23301' ---> ' 1.23301' (with left_pad=2)
        This option is useful when displaying numbers in a column and having
        them all line up nicely with the decimal points.
    right_pad: int
        width of the portion of the number following the decimal point.
        Trailing whitespace padding relative to decimal point.
        eg.:
            '1.233' ---> ' 1.233  ' (with right_pad=6)
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

    # pad relative to decimal position
    left_pad, left_pad_char = _check_pad(left_pad)
    right_pad, right_pad_char = _check_pad(right_pad)

    # automatically decide on a precision value if not given
    m = None
    if (precision is None) or (left_pad > 0) or (right_pad > 0):
        # order of magnitude and `significant` determines precision
        m = order_of_magnitude(n)
        if np.isinf(m):
            m = 0
        if precision is None:
            precision = int(significant) - m - 1

    precision = max(precision, 0)
    # TODO: precision < 0 do rounding

    # format the number
    _1000fmt = ',' if thousands else ''
    s = f'{n:{sign_fmt}{_1000fmt}.{precision}f}'.replace(',', thousands)

    if unicode:
        s = s.replace('inf', '∞')

    # pad with whitespace relative to decimal position. useful when displaying
    # arrays of decimal numbers.
    # Left pad used and we need to line up with decimal position of larger
    # numbers.
    if left_pad > 0:  # need this to know if m is in namespace!!!
        if left_pad > min(m, 0):
            # total display width
            w = left_pad + precision + int(precision > 0)
            #                        ⤷ +1 if number has decimal point
            s = s.rjust(w, left_pad_char)

    # strip redundant zeros
    n_stripped = 0
    width = len(s)
    if precision > 0 and compact:
        # remove redundant zeros
        s = s.rstrip('0').rstrip('.')
        n_stripped = width - len(s)

    # Right pad for when numbers are displayed to various precisions and the
    # should form a block. eg. nrs followed by a 1σ uncertainty, and we want to
    # line up with the '±'.
    # eg.:
    #   [-12   ± 1.2,
    #      1.1 ± 0.2 ]

    if right_pad >= max(precision - n_stripped, 0):
        # compute required width of formatted number string
        m = m or order_of_magnitude(n)
        w = sum((int(bool(sign) & (n < 0)),
                 max(left_pad, m + 1),  # width lhs of '.'
                 max(right_pad, precision),  # width rhs of '.'
                 int(precision > 0)))  # '.' expected in formatted str?

        s = s.ljust(w, right_pad_char)

    if unicode:
        s = s.replace('-', '−')
    return s


def decimal_with_percentage(n, total, precision=None, significant=3, sign='-',
                            compact=False, unicode=False, left_pad=0,
                            right_pad=0, thousands='', brackets='()'):
    if isinstance(precision, sequences):
        p0, p1 = precision
    else:
        p0 = p1 = precision

    d = decimal(n, p0, significant, sign, compact,
                unicode, left_pad, right_pad, thousands)
    p = '{:.{}%}'.format(n / total, p1)
    return d + p.join(brackets)


def sci(n, significant=5, sign=False, times='x',  # x10='x' ?
        compact=False, unicode=None, latex=None, engineering=False):
    r"""
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
                latex:      '\times'    or      '\cdot'
                str:         'x'        or      '*'
        * using 'E' or 'e' will switch to E-notation style. eg.: 1.3e-12
        * Any other str may be passed in which case it will be used verbatim.
    compact: bool
        should redundant zeros after decimal point be stripped to yield a
        more compact representation of the same number?
    unicode: bool
        prefer unicode minus symbol '−' over '-'
        prefer unicode infinity symbol  '∞' over 'inf'
        prefer unicode multiplication symbol '×' over 'x'
    latex:
        represent the number as a latex string:
        eg:. '$1.04 \times 10^{-12}$'
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
            times = UNI_MULT.get(times, times)
            pwr_sgn = ['', UNI_NEG_PWR][m < 0]
            exp = pwr_sgn + UNI_PWR.get(abs(m), '')
        else:
            pwrFmt = '%i'
            if latex:
                pwrFmt = '^{%i}'
                times = LATEX_MULT.get(times, times)
            exp = '' if m == 1 else pwrFmt % m

    #
    # if compact:
    #     # short representation of number eg.: 10000  ---> 1e5  or 10⁵
    #     raise NotImplementedError

    # finally bring it all together
    v = n * (10 ** -m)  # coefficient / mantissa / significand as float
    # mantissa as str
    mantis = decimal(v, None, significant, sign, compact, unicode)

    # mantis = formatter(v)

    # concatenate
    r = ''.join([mantis, times, base, exp])

    if latex:
        return '$%s$' % r
        # TODO: make this wrap optional. since decimal does not do this
        #  integration within numeric is bad

    return r


def numeric(n, precision=3, significant=3, log_switch=5, sign='-', times='x',
            compact=True, thousands='', unicode=None, latex=None,
            engineering=False):
    """

    Parameters
    ----------
    significant
    n
    precision
    log_switch: int # TODO: tuple  # TODO: log_switch better name
        Controls switching between decimal/scientific notation. Scientific
        notation is triggered if `abs(math.log10(abs(n))) > switch`.

    compact
        TODO: If compact = True
        Default is chosen in such a way that the representation of the number
        is as compact as possible. eg: '1.01445 × 10²' can be more compactly
        represented as '101.445'; 1000 can be more compactly represented as
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

    # if compact:
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
        return decimal(n, precision, None, sign, compact, unicode,
                       thousands=thousands)

    return sci(n, significant, sign, times, compact, unicode, latex,
               engineering)


nr = numeric


def numeric_array(n, precision=2, significant=3, log_switch=5, sign=' ',
                  times='x', compact=False, unicode=None, latex=None,
                  engineering=False, thousands=''):
    """Pretty numeric representations for arrays of scalars"""
    # note default args slightly different:
    #   sign ' ' instead of '-'  for alignment
    return vectorize(numeric)(n, precision=precision, significant=significant,
                              log_switch=log_switch, sign=sign, times=times,
                              compact=compact, thousands=thousands,
                              unicode=unicode, latex=latex,
                              engineering=engineering)


# ------------------------------------------------------------------------------
# Uncertainties:
# ------------------------------------------------------------------------------

# TODO: precision_rules: 'uipac', 'uipap' ??
def precision_rule_dpg(u):
    # Data Particle Group rules
    # http://pdg.lbl.gov/2010/reviews/rpp2010-rev-rpp-intro.pdf (section 5.4:
    #  Rounding, pg 13)

    # ""The basic rule states that if the three highest order digits of the error(sic) lie between 100
    # and 354, we round to two significant digits. If they lie between 355 and 949, we round
    # to one significant digit. Finally, if they lie between 950 and 999, we round up to 1000
    # and keep two significant digits. In all cases, the central value is given with a precision
    # that matches that of the error (sic). So, for example, the result (coming from an average)
    # 0.827 ± 0.119 would appear as 0.83 ± 0.12, while 0.827 ± 0.367 would turn into 0.8 ± 0.4.""

    nrs, m = get_significant_digits(u, 3)
    #
    if 100 <= nrs < 355:
        r = 1  # round to two significant digits
    elif 355 < nrs < 950:
        r = 0  # round to one significant digit
    else:
        r = -1  # round up to 1000 and keep two significant digits
    return -m + r  # precision


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


def decimal_u(x, u, precision=None, compact=False,
              sign=False, unicode=True, latex=False):
    """
    Represent a number with associated standard deviation uncertainty as str.


    Parameters
    ----------
    x
    u
    precision
    compact
    sign
    unicode
    latex

    Returns
    -------

    """
    if precision is None:
        precision = precision_rule_dpg(u)
    precision = int(precision)  # type enforcement

    xr = decimal(x, precision, 0, sign, compact)
    ur = decimal(u, precision, 0, '', compact)

    if unicode:
        return '%s ± %s' % (xr, ur)

    if latex:
        return r'$%s \pm %s$' % (xr, ur)

    return '%s +/- %s' % (xr, ur)


# def vectorize():
#     # handle masked arrays
#     if np.ma.is_masked(xr):
#         xr = np.ma.filled(xr, str(np.ma.masked))


def uarray(x, u, significant=None, switch=5, compact=False, times='x',
           sign='-', unicode=True, latex=False,
           engineering=False):
    """

    Parameters
    ----------
    x
    u
    precision
    compact:
        default False since compactly represented numbers in arrays will be
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

    # decide on scientific vs decimal notation
    logn = np.log10(abs(x))
    oom = np.floor(np.round(logn, 9)).astype(int)
    mmin, mmax = oom.min(), oom.max()
    mag_rng = mmax - mmin  # dynamic range in order of magnitude
    if mag_rng > switch:
        'use sci for entire array'
        raise NotImplementedError
    else:
        # use decimal representation for entire array
        # TODO: def decimal_repr_array():

        if significant is None:
            # get precision values from the Data Particle Group rules
            precision = vectorize(precision_rule_dpg)(u).max()
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
        xr = vectorize(decimal_u)(x, u, precision=precision,
                                  compact=compact, sign=sign,
                                  unicode=unicode, latex=latex)

        return xr

        # option 2

        # return xr

    # σ = unp.std_devs(a)
    # return list(map(leading_decimal_zeros, σ))


def sci_array(n, significant=5, sign='-', times='x',  # x10='x' ?
              compact=False, unicode=None, latex=None, engineering=False):
    """Scientific representation for arrays of scalars"""
    # masked data handled implicitly by vectorize
    # from recipes.array.misc import vectorize

    return vectorize(sci)(n, significant=significant, sign=sign,
                          times=times, compact=compact, unicode=unicode,
                          latex=latex, engineering=engineering)


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
                minimalist=True, title='', title_props={})
    n_rows, _ = tbl.shape
    left = '\n'.join('┌' + ('│' * n_rows) + '└')
    right = '\n'.join([' ┐'] + [' │'] * n_rows + [' ┘'])
    return hstack([left, tbl, right])


# def matrix(a, precision=2, significant=3, switch=5, sign=' ', times='x',
#           compact=False, unicode=True, latex=False, engineering=False,
#           thousands=''):
#     """"""
#     q = numeric_array(a, precision, significant, switch, sign, times, compact,
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
                                         compact=self.minimalist)

        # for str, return the str instead of its repr
        if isinstance(obj, str):
            return obj

        # TODO: figure out how to do recursively for array_like

        return pprint.PrettyPrinter.pformat(self, obj)

# def leading_decimal_zeros(n):  #
#     """
#     Gives the number of 0's following the decimal point and preceding the most
#     significant digit in the decimal representation of a number. Note that this
#     function will return the correct number of leading zeros for numbers
#     represented in scientific *as though those numbers where represented as
#     decimal*.
#
#     Parameters
#     ----------
#     n: number
#
#     Examples
#     --------
#     >>> leading_decimal_zeros(0.0000001) # 6
#     >>> leading_decimal_zeros(100.0000001) # 6
#     >>> leading_decimal_zeros(12e-23) # returns 21
#
#     Returns
#     -------
#
#     """
#     if not isinstance(n, numbers.Real):
#         raise ValueError('Only scalars are accepted by this function.')
#
#     rn = repr(n)
#     # try match decimal notation: eg.: '3.14159'
#     match = DECIMAL_SRE.match(rn)
#     if match:
#         return len(match.group(1))
#
#     # try match scientific notation: eg.: '1e-05'
#     match = SCI_SRE.match(rn)
#     if match:
#         return int(match.group(1)) - 1
#
#     return 0

# def minimalist_decimal_format(n, precision=None):
#     """
#     Minimalist decimal representation of float as str with given decimal
#     precision.
#
#     Parameters
#     ----------
#     n: int or float
#         the number to format
#     precision: int, optional
#         decimal precision for format.
#         default is 1 if the abs(number) is larger than 1. Otherwise it is chosen
#         such that at least 3 non-zero digits are shown: eg: 0.0000345 or 0.985
#
#     Returns
#     -------
#     str
#
#     Examples
#     --------
#     >>> minimalist_decimal_format(2.0000001, 3)
#     '2'
#     >>> minimalist_decimal_format(3.14159265, 5)
#     '3.14159'
#     """
#

# def leading_decimal_zeros(n):
#     absn = abs(n)
#     deci = absn - int(absn)
#     print(deci, np.log10(deci), -(np.log10(deci) + 1))
#     if deci == 0:
#         return 0
#     return -int(np.log10(deci) + 1)


# def minimalist_decimal_format(n, precision=1):
#     """minimal numeric representation of floats with given precision"""
#     return '{:g}'.format(round(n, precision))


# def sciFormat(x, precision=2, times=r'\times'):
#
#     if x == 0:
#         val = 0
#     else:
#         s = np.sign(x)
#         xus = abs(x)
#         lx = np.log10(xus)
#         pwr = np.floor(lx)
#         val = s * xus * 10 ** -pwr
#
#     valstr = '{:.{}f}'.format(val, precision)
#     return r'$%s%s10^{%i}$' % (valstr, times, pwr)


# def switchlogformat(x, precision=2, switch=3, times=r'\times'): #unicode minus???
#
#     if x == 0:
#         return '0'
#
#     s = list(' -')[np.sign(x) < 0]
#     xus = abs(x)
#     lx = np.log10(xus)
#     pwr = np.floor(lx)
#
#     if abs(pwr) < switch:
#         return minimalist_decimal_format(x, precision)
#
#     val = xus * 10 ** -pwr
#     valstr = minimalist_decimal_format(val, precision)
#
#     if valstr == '1':
#         return r'$%s10^{%i}$' % (s, pwr)
#
#     return r'$%s%s%s10^{%i}$' % (s, valstr, times, pwr)


# def minlogformat(x, precision=2, times=r'\times'): #unicode minus???
#
#     if x == 0:
#         return '0'
#
#     s = ['', '+', '-'][np.sign(x)]
#     xus = abs(x)
#     lx = np.log10(xus)
#     pwr = np.floor(lx)
#
#     if abs(pwr) < precision:
#         return minimalist_decimal_format(x, precision)
#
#     val = xus * 10 ** -pwr
#     valstr = minimalist_decimal_format(val, precision)
#
#     if valstr == '1':
#         return r'$%s10^{%i}$' % (s, pwr)
#
#     return r'$%s%s%s10^{%i}$' % (s, valstr, times, pwr)

# minlogfmt = minlogformat


# def switchlogfmt(x, precision=2, switch=3, minimalist=True, times=r'\times'):
#
#     v = 10 ** switch
#     if abs(x) >= v:
#         fmt = minlogfmt if minimalist else sciFormat
#         fmt = functools.partial(fmt, times=times, precision=precision)
#     else:
#         fmt = minimalist_decimal_format if minimalist else '{:.{precision}f}'.format
#         fmt = functools.partial(fmt, precision=precision)
#     return fmt(x)

# def rformat(item, precision=None, minimalist=True):
#     """
#     Apply numerical formatting recursively for arbitrarily nested iterators,
#     optionally applying a conversion function on each item.
#
#     precision: int, optional
#         decimal precision for format.
#         default is 1 if the abs(number) is larger than 1. Otherwise it is chosen
#         such that at least 3 non-zero digits are shown: eg: 0.0000345 or 0.985
#     minimalist: bool
#         whether to include non-significant decimals in the float representation
#         if True (default), will always show to given precision.
#             eg. with precision=5: 7.0001 => 7.00010
#         if False, show numbers in the shortest possible format given precision.
#             eg. with precision=3: 7.0001 => 7
#     """
#     if isinstance(item, str):
#         return item
#
#     if minimalist:
#         floatFormatFunc = decimal
#     else:
#         floatFormatFunc = '{:.{}f}'.format
#         precision = precision or 3
#
#     if isinstance(item, (int, float)):
#         return floatFormatFunc(item, precision)
#
#     try:
#         # Handle array_like items with len(item) in [0,1] here
#         # np.asscalar converts np types to python builtin types (Phew!!)
#         # NOTE: This will suppress the type representation of the object str
#         builtin_type = np.asscalar(item)
#         if isinstance(builtin_type, str):
#             return str(item)
#
#         if isinstance(builtin_type, (int, float)):
#             return floatFormatFunc(item, precision)
#
#     except Exception as err:
#         # Item is not str, int, float, or convertible to such...
#         pass
#
#     if isinstance(item, np.ndarray):
#         return np.array2string(item, precision=precision)
#         # NOTE:  lots more functionality here
#
#     return str(item)
#     # return pformat(item)
#
#     # brackets = { tuple : '()', set : '{}', list : '[]' }
#     # if np.iterable(item):
#
#     # if isinstance(item, (tuple, set, list)):
#     # br = list(brackets[type(item)])
#     # else:
#     # warn( 'NEED FMT FOR: {}'.format(type(item)) )
#     # br = '[]'        #SEE ALSO:  np.set_print_options
#
#     # recur = ft.partial(rformat, precision=precision)         #this way it works with iterators that have no __len__
#     # return ', '.join( map(recur, item) ).join(br)
#
#     # else:       #not str, int, float, or iterable
#     # return str(item)
