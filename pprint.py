# builtin libs
import re
import math
import pprint
import numbers
from functools import partial

# third-party libs
from IPython import embed

# TODO: numbers with uncertainty!!!!

# Unicode
UNI_PWR = dict(enumerate('²³⁴⁵⁶⁷⁸⁹', 2))  # '¹²³⁴⁵⁶⁷⁸⁹'
UNI_NEG_PWR = '⁻'  # '\N{SUPERSCRIPT MINUS}'
UNI_PM = '±'
UNI_MULT = {'x': '×', '.': '·'}
# '\N{MINUS SIGN}'              '−'     u'\u2212'
# '\N{PLUS-MINUS SIGN}'         '±'
# '\N{MULTIPLICATION SIGN}'     '×' 	u'\u00D7'
# '\N{MIDDLE DOT}'              '·'     u'\u00B7'
# '\N{INFINITY}                 '∞'     u'\u221E'
# convert unicode to hex-16: '%x' % ord('⁻')

# LaTeX
LATEX_MULT = {'x': r'\times', '.': '\cdot'}

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


def decimal_repr(n, precision=None, significant=3, sign='-', compact=False,
                 unicode=False, left_pad=0, right_pad=0):
    """
    Minimalist decimal representation of float as str up to given number
    of significant digits (relative), or decimal precision (absolute).

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
        after the decimal point that will be displayed
    sign: str or bool
        True: always sign; False: only negative
        '+' or '-' or ' ' like builtin format spec
    compact : bool
        should redundant zeros and decimal point be stripped?
    unicode:
        prefer unicode minus '−' over '-'
        prefer unicode infinity '∞' over 'inf'
    left_pad: int
        width of the portion of the number preceding the decimal point.  If
        number string is shorter than `left_pad`, whitespace will be pre-padded.
        eg.:
            '1.23301' ---> ' 1.23301' (with left_pad=2)
    right_pad: int
        width of the portion of the number following the decimal point.
        Trailing whitespace padding relative to decimal point.
        eg.:
            '1.233' ---> ' 1.233  ' (with right_pad=5)

    # TODO: options for thousand_separator spaces or commas

    Returns
    -------
    str

    Examples
    --------
    >>> decimal_repr(2.0000001, 3)
    '2'
    >>> decimal_repr(3.14159265, 5)
    '3.14159'
    """
    # ensure we have a scalar
    if not isinstance(n, numbers.Real):
        raise ValueError('Only scalars are accepted by this function.')

    if math.isinf(n):
        if unicode:
            return ('', '−')[n < 0] + '∞'  # TODO: case sign == '+'
        return str(n)  # 'inf'

    # pad relative to decimal position
    # assert isinstance(left_pad, numbers.Integral)
    left_pad = int(left_pad)
    right_pad = int(right_pad)

    # automatically decide on a precision value if not given
    if (precision is None) or (left_pad > 0) or (right_pad > 0):
        # order of magnitude and `significant` determines precision
        m = order_of_magnitude(n)
        if precision is None:
            precision = int(significant) - m - 1

    precision = max(precision, 0)
    # TODO: precision < 0

    # get sign
    if isinstance(sign, bool):
        sign = '-+'[sign]
    if not isinstance(sign, str) or sign not in ' -+':
        raise ValueError('Invalid sign %r. Use one of "+", "-", " ". Set '
                         '`unicode=True` if you want a unicode minus.')
    # if sign not in ' -+':
    #     raise ValueError('Invalid sign %r. Use one of "+", "-", " ". Set '
    #                      '`unicode=True` if you want a unicode minus.' % sign)
    sign_fmt = sign

    # format the number
    s = '{:{}.{}f}'.format(n, sign_fmt, precision)
    # s = '{: >{}{}.{}f}'.format(n, sign_fmt, w, precision)
    # return s
    # pad with whitespace relative to decimal position. useful when displaying
    # arrays of decimal numbers.
    # Left pad used and we need to line up with decimal position of larger
    # numbers.

    if left_pad > 0:
        # tells us m is in the namespace
        if left_pad > min(m, 0):
            # total display width
            w = left_pad + precision + int(precision > 0)
            #                        ⤷ +1 if number has decimal point
            # +1 since number with order of magnitude of 1 has width of 2
            s = s.rjust(w)

    # strip redundant zeros
    n_stripped = 0
    if precision > 0:
        l = len(s)
        if compact:
            # remove redundant zeros
            s = s.rstrip('0').rstrip('.')
            n_stripped = l - len(s)

    # Right pad for when numbers are displayed to various precisions and the
    # should form a block. eg. nrs followed by a 1σ uncertainty, and we want to
    # line up with the '±'.
    # eg.:
    #   [-12   ± 1.2,
    #      1.1 ± 0.2 ]

    if right_pad > max(precision - n_stripped, 0):
        w = max(right_pad, precision) + max(left_pad, m + 1) \
            + int(('.' not in s))  # +1 if repr has dot
        s = s.ljust(w)

    if unicode:
        s = s.replace('-', '−')
    return s

    # TODO: signed better


def sci_repr(n, significant=5, sign=False, times='x',  # x10='x' ?
             compact=False, unicode=True, latex=False, engineering=False):
    r"""
    Scientific numeral representation strings in various formats.
    See:  https://en.wikipedia.org/wiki/Scientific_notation

    Parameters
    ----------
    n: scalar
        The number to be represented
    significant: int
        Number of significant figures to display.
    compact: bool
        should redundant zeros after decimal point be stripped to yield a
        more compact representation of the same number?
    times: str
        style to use for multiplication symbol.
        * If value is either 'x' or '.':
            The symbol used is decided based on the unicode and latex flags
            as per the following:
                unicode:    '×'         or      '·'
                latex:      '\times'    or      '\cdot'
                str:         'x'        or      '*'
        * using 'E' or 'e' will switch to E-notation style. eg.: 1.3e-12
        * Any other str may be passed in which case it will be used verbatim.
    sign: bool
        add '+' to positive numbers
    unicode: bool
        prefer unicode minus '−' over '-'
        prefer unicode infinity '∞' over 'inf'
        prefer unicode multiplication '×' over 'x'
    latex:
        represent the number as a latex string:
        eg:. '$1.04 \times 10^{-12}$'
    engineering: bool
        Prefer representation where exponent is a multiple of 3. Essentially
        scientific notation with base 1000.


    # TODO: spacing options
    # todo: SI prefixes

    Returns
    -------
    str
    """
    # ensure we have a scalar
    if not isinstance(n, numbers.Real):
        raise ValueError('Only scalars are accepted by this function.')

    # check flags
    assert not (unicode and latex)  # can't do both!

    #
    n_ = abs(n)
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
                pwrFmt = '{%i}'
                times = UNI_MULT.get(times, times)
            exp = '' if m == 1 else pwrFmt % m

    #
    # if compact:
    #     # short representation of number eg.: 10000  ---> 1e5  or 10⁵
    #     raise NotImplementedError

    # finally bring it all together
    v = n * (10 ** -m)  # coefficient / mantissa / significand as float
    # mantissa as str
    mantis = decimal_repr(v, None, significant, sign, compact, unicode)

    # mantis = formatter(v)

    # concatenate
    r = ''.join([mantis, times, base, exp])

    if latex:
        return '$%s$' % r

    return r


def numeric_repr(n, precision=2, switch=5, sign='-', times='x',
                 compact=True, unicode=True, latex=False, engineering=False):
    """

    Parameters
    ----------
    n
    precision
    switch: int
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

    Returns
    -------

    """
    # ensure we have a scalar
    if not isinstance(n, numbers.Real):
        raise ValueError('Only scalars are accepted by this function.')
    # check special behaviour flags
    assert not (unicode and latex)  # can't do both!

    # n_ = abs(n)
    m = order_of_magnitude(n)  # might be -inf

    # if compact:
    #     formatter = partial(decimal_repr, precision=precision)
    # else:
    #     formatter = ('{:.%if}' % precision).format

    if switch is False:
        # always display decimal format
        switch = math.inf
    if switch is True:
        # always display log format
        switch = 0
    if switch is None:
        # decide format based on precision
        switch = precision
    # TODO lower and upper switch...

    # m = order_of_magnitude(n)
    if math.isinf(m) or abs(m) < switch:
        # handle case n == 0 and normal float formatting
        return decimal_repr(n, precision, 'ignored', sign, compact, unicode)

    return sci_repr(n, precision, sign, times, compact, unicode, latex,
                    engineering)


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


def decimal_repr_u(x, u, precision=None, compact=False,
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

    xr, ur = (decimal_repr(y, precision, 0, compact, sign=sign)
              for y in (x, u))

    if unicode:
        return '%s ± %s' % (xr, ur)

    if latex:
        return '$%s \pm %s$' % (xr, ur)

    return '%s +/- %s' % (xr, ur)


def pprint_uarray(x, u, significant=None, compact=False, times='x',
                  sign=False, unicode=True, latex=False,
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
    # Note: numpy offers now way of formatting arrays where the formatting is
    #  decided based on the number of array elements that will be displayed.
    # this needs a PR!!!

    # TODO;
    # max_line_width=None, precision=None,
    # suppress_small=None, separator=' ', prefix="",
    # style=np._NoValue, formatter=None, threshold=None,
    # edgeitems=None, sign=None, floatmode=None, suffix=""

    import numpy as np
    # It's important here to line up the various parts of the representation
    # so that the numbers can easily be compared scrolling your eye along a
    # column. We also might want uniform magnitude scaling across the array.

    if np.size(x) > 1000:
        raise NotImplementedError

    # decide on scientific vs decimal notation
    logn = np.log10(abs(x))
    oom = np.floor(np.round(logn, 9)).astype(int)
    mmin, mmax = oom.min(), oom.max()
    mag_rng = mmax - mmin  # dynamic range in order of magnitude
    if mag_rng > 3:
        'use sci_repr for entire array'
        raise NotImplementedError
    else:
        # use decimal representation for entire array
        # TODO: def decimal_repr_array():

        if significant is None:
            pmax = np.vectorize(precision_rule_dpg)(u).max()

        # get plus-minus character
        if unicode:
            pm = UNI_PM
        elif latex:
            pm = '\pm'
        else:
            pm = '+-'
        # spacing
        pm = ' %s ' % pm

        # here we can either display all digits for all elements up to
        # `significant` or we can fill trailing whitespace up to `significant`.

        # option 1
        xr = np.vectorize(decimal_repr)(x, pmax, compact=False, sign=' ', )
        ur = np.vectorize(decimal_repr)(u, pmax, None, False)
        return list(map(pm.join, zip(xr, ur)))

        # option 2

        return xr

    # σ = unp.std_devs(a)
    # return list(map(leading_decimal_zeros, σ))


def sci_repr_array():
    """Scientific representation for arrays of scalars"""


#
class PrettyPrinter(pprint.PrettyPrinter):
    """Hack the PrettyPrinter for custom handling of float, int and str types"""

    def __init__(self, indent=1, width=80, depth=None, stream=None, *,
                 compact=False, precision=None, minimalist=True):

        if minimalist:
            self._floatFormatFunc = decimal_repr
        else:
            self._floatFormatFunc = '{:.{}f}'.format
            precision = precision or 3

        self.precision = precision

        super().__init__(indent, width, depth, stream, compact=compact)

    def pformat(self, obj):
        """
        Format object for a specific context, returning a string
        and flags indicating whether the representation is 'readable'
        and whether the object represents a recursive construct.
        """
        # intercept float formatting
        if isinstance(obj, (int, float)):
            return self._floatFormatFunc(obj, self.precision)

        # for str, return the str instead of its repr
        if isinstance(obj, str):
            return obj

        # TODO: figure out how to do recursively for array_like

        return pprint.PrettyPrinter.pformat(self, obj)


if __name__ == '__main__':
    # Tests

    assert leading_decimal_zeros(0.0001) == 3
    assert leading_decimal_zeros(1000.0001) == 3
    assert leading_decimal_zeros(12e-23) == 21

    assert decimal_repr(3.14159265, 5) == '3.14159'
    assert decimal_repr(2.0000001, 3) == '2'
    assert decimal_repr(2.01000001, 1) == '2'
    assert decimal_repr(2.01000001, 2) == '2.01'

    # test padding
    import random

    for i in range(10):
        p = 6
        l = random.randrange(0, 10)
        r = random.randrange(0, 10)
        s = decimal_repr(40.3344000, precision=p, left_pad=l, right_pad=r)
        i, d, e = s.partition('.')
        assert len(i) >= l
        assert len(d + e) == max(r, p + 1)

# Regex matchers for decimal and scientific notation
# SCI_SRE = re.compile('[+-]?\d\.?\d?e[+-]?(\d\d)', re.ASCII)
# DECIMAL_SRE = re.compile('[+-]?\d+\.(0*)[1-9][\d]?', re.ASCII)

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
#         floatFormatFunc = decimal_repr
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


