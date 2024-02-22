"""
Formatters for numeric types and arrays.
"""

# std
import math
import numbers
import warnings
from typing import Union
from collections import abc
from fractions import Fraction

# third-party
import numpy as np
from loguru import logger

# relative
from ..string import unicode
from ..array import vectorize
from ..containers import dicts
from ..oo import classproperty
from ..math import order_of_magnitude, signum
from ..containers.utils import duplicate_if_scalar
from .callers import describe
from .nrs import precision_rule_dpg


# ASCII_MAP = {'inf': 'inf'}

# unicode
UNICODE_MAP = {'inf':  '\N{INFINITY}',             # '∞'
               '-':    '\N{MINUS SIGN}',           # '−'
               '+/-':  '\N{PLUS-MINUS SIGN}',      # '±'
               'x':    '\N{MULTIPLICATION SIGN}',  # '×'
               '.':    '\N{MIDDLE DOT}'}           # '·'
# ⏨  Decimal exponent symbol
# ⒑  NumberBase Ten Full Stop
# ⑽ Parenthesized NumberBase Ten

# LaTeX
LATEX_MAP = {'inf': R'\infty',
             'x':   R'\times',
             '.':   R'\cdot'}

LATEX_WRAP = {
    None:       ('', ''),
    '':         ('', ''),
    '\(':       ('\(', '\)'),
    '$':        '$$',
    '$$':       ('$$', '$$')
}

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

# ---------------------------------------------------------------------------- #


def empty_string(_):
    return ''


def resolve_sign(signed, allowed=' -+'):
    if signed is None:
        return ' '

    if isinstance(signed, bool):
        return '-+'[signed]

    if isinstance(signed, str) and ((allowed is any) or (signed in allowed)):
        return signed

    raise ValueError(f'Invalid value {signed!r} for `signed` parameter. Use one'
                     f' of {tuple(allowed)}.')

# ---------------------------------------------------------------------------- #


def _rhs(obj):
    return 'None' if obj is None else repr(str(obj))


class SlotHelper:
    __slots__ = ()

    def __str__(self):
        return self._repr(type(self).__slots__,
                          lhs=str, equal='=', rhs=repr,
                          brackets='()', align=False)

    def __repr__(self):
        # (_ for base in (*type(self).__bases__, type(self))
        return self._repr(type(self).__slots__)

    def _repr(self, attrs, **kws):
        kws.setdefault('rhs', _rhs)
        return dicts.pformat({_: getattr(self, _) for _ in attrs},
                             type(self).__name__,
                             **kws)

    def __init__(self, **kws):
        kws.pop('self', None)
        kws.pop('kws', None)
        kws.pop('__class__', None)
        for key, val in kws.items():
            setattr(self, key, val)


# ---------------------------------------------------------------------------- #


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

    def __init__(self, total, fmt_nr, precision=None, brackets='()'):

        self.total = float(total)
        self.formatter = fmt_nr

        # precision for percentage value
        self.precision = precision
        if precision is None:
            self.precision = getattr(fmt_nr, 'precision', 0)

        fmt_p = f'{{f:.{self.precision}%}}'.join(brackets)
        self._fmt = f'{{x}} {fmt_p}'

    def __call__(self, x):
        return self._fmt.format(x=self.formatter(x), f=x / self.total)


# ---------------------------------------------------------------------------- #
class FormatterConstructors:

    @classmethod
    def as_percentage_of(cls, total, **kws):
        return Percentage(total, cls(**kws))

    @classproperty
    def ascii(cls):  # sourcery skip: instance-method-first-arg-name
        return cls(*cls._presets['ascii'])

    @classproperty
    def unicode(cls):  # sourcery skip: instance-method-first-arg-name
        """
        A representation prefering unicode characters
            '−' MINUS SIGN      over '-'
            '∞' INFINITY        over 'inf'
            '±' PLUS-MINUS SIGN over '+/-'

        Parameters
        ----------
        x : number.Real
            [description]

        Examples
        --------
        >>> 
        """
        # for atr in self.__slots__:
        return cls(*cls._presets['unicode'])
        # return strings.sub(self(x), UNICODE_MAP)

    @classproperty
    def latex(cls):  # sourcery skip: instance-method-first-arg-name
        return cls(*cls._presets['latex'])  # .join(LATEX_WRAP[math])

    def map(self, x: abc.Collection):
        return list(map(self, x))

    def array(self, **kws):
        return Array(self, **kws)


# @dataclass
class NumberBase(FormatterConstructors, SlotHelper):
    """Base class for dynamic number formatting."""

    # # _: KW_ONLY    # 3.10+ only
    # inf: str = field(default='inf', repr=False)
    # nan: str = field(default='nan', repr=False)
    # masked: str = field(default='--', repr=False)

    __slots__ = ('inf', 'nan', 'masked')

    _presets = {
        'ascii':    ('inf', 'nan', '--'),
        'unicode':  ('\N{INFINITY}', 'nan', '\N{BLACK SQUARE}'),  # '∞' '■'
        'latex':    (R'\infty', 'nan', '--')
    }

    def __init__(self, inf: str = 'inf', nan: str = 'nan', masked: str = '--',
                 **kws):

        kws = {**locals(), **kws}
        kws.pop('self')
        super().__init__(**kws)

    def validate(self, x):
        # ensure we have a scalar
        if not isinstance(x, numbers.Real):
            raise ValueError('Only scalars are accepted by this function, found'
                             f' {type(x)}.')

    # @api.validate(x=validate)
    def __call__(self, x: numbers.Real):
        """
        x: int or float
            the number to format
        """
        # ensure we have a scalar
        self.validate(x)

        # handel masked values
        if isinstance(x, np.ma.core.MaskedConstant):
            return self.masked

        # handle nans
        if math.isnan(x):
            return self.nan

        if math.isinf(x):
            return self.inf

        return self.format(x)

    def format(self, x, precision=None):
        """
        x: int or float
            the number to format
        precision: int
            numberic precision
        """
        raise NotImplementedError

    #     spec =  f'{self.signed}{","[:bool(self.thousands)]}.{precision}f'
    #     # self.get_spec(*args, precision)
    #     xr = format(x, spec).replace(',', self.thousands)

    #     # strip redundant zeros
    #     if self.short and precision > 0:
    #         # remove redundant zeros
    #         xr = xr.rstrip('0').rstrip('.')

    #     return xr

    # def get_spec(self, precision):
        # return f'{self.signed}{","[:bool(self.thousands)]}.{precision}f'

    # def metric(self, x):
    #     return self(x)

    def shortest(self, x, choices=KNOWN_FORMATS):
        """
        Most compact representation possible from amongst formats `choices`.

        Parameters
        ----------
        x : [type]
            [description]

        Examples
        --------
        >>> 

        Returns
        -------
        [type]
            [description]
        """
        raise NotImplementedError('todo')


# @api.validate(signed=resolve_sign)
# @dataclass


class Decimal(NumberBase):
    """
    Decimal number formatter.
    This produces decimal format strings of numeric type objects. The
    `significant` parameter controls the number of (non-zero) significant digits
    that are displayed, while the mutually exclusive `precision` parameter
    controls the absolute number of digits after the decimal period. Minimalist,
    or `short` representations can be requested, in which case trailing zeros
    and decimal point are removed.

    TODO: optional left- and right padding and unicode representation of
    minus/infinity (−/∞) included.

    Parameters
    ----------
    precision: int, optional
        if int:
            Absolute decimal precision for format.
        if None, the default:
            precision = 1 if the `abs(number)` is larger than 1. eg. 100.1
            Otherwise it is chosen such that at least 3 significant digits
            are shown: eg: 0.0000345 or 0.985 (see `significant` parameter).
    significant : int, optional
        If precision is not given, this gives the number of non-zero digits
        after the decimal point that will be displayed. This argument allows
        specification of dynamic precision values which is useful when
        dealing with numbers that have a large dynamic range.
    signed: str or bool, optional
        '-' or True: always signed.
        '+' or False: only sign negative numbers.
        ' ' or None: sign negative numbers, add space before positive.
    thousands: str, optional
        Thousands separator.
    short : {True, False, -1}
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
    >>> Decimal(3)(2.0000001)
    '2'
    >>> Decimal(5)(3.14159265)
    '3.14159'
    """
    __slots__ = ('precision', 'significant', 'signed', 'thousands', 'short')

    # @api.synonyms({'sig|digits': 'significant',
    #                'thousand|_1000': 'thousands',
    #                'sign': 'signed',
    #                'shorten': 'short'})
    def __init__(self,
                 significant: int = 3,
                 precision: int = None,
                 thousands: str = '',
                 signed: Union[str, bool] = '-',
                 short: Union[str, bool] = True,
                 **kws):
        # if significant == 0 and precision is None:
        #     precision = 0
        #     significant = 1

        if significant < 0:
            raise ValueError('NumberBase of `significant` digits must be positive '
                             'non-zero.')

        kws = {**locals(), **kws}
        kws.pop('self')
        super().__init__(**kws)

    def __str__(self):
        attrs = list(self.__slots__)
        attrs.pop(0 if self.precision is None else 1)
        return self._repr(attrs,
                          lhs=str, equal='=', rhs=repr,
                          brackets='()', align=False)

    def __repr__(self):
        return self._repr(type(self).__slots__)

    def format(self, x, /, precision=None):
        """
        x: int or float
            the number to format
        """

        precision = self._get_precision(precision, x)

        # format the number
        spec = f'{self.signed}{","[:bool(self.thousands)]}.{precision}f'
        xr = format(x, spec).replace(',', self.thousands)

        # strip redundant zeros
        if self.short and precision != 0:
            # remove redundant zeros
            width = len(xr)
            xr = xr.rstrip('0').rstrip('.')
            if self.short == ' ':
                xr += ' ' * width - len(xr)

        return xr

    def _get_precision(self, precision, x):
        # decide default precision
        precision = precision or self.precision
        if (precision is not None):
            return precision

        if x >= 1:
            return self.significant

        # if x == 0:
        #     return 0

        # order of magnitude and `significant` determines precision
        m = order_of_magnitude(x)
        # if math.isinf(m):
        #     m = 0

        precision = int(self.significant) - min(m, 1) - 1

        # only positive precision value make sense for decimal format
        if precision < 0:
            warnings.warn(f'Negative precision not allowed for '
                          f'{describe(type(self))}. Setting precision to 0.')
            return 0

        logger.debug('Using precision {} for {} significant digits.',
                     precision, self.significant)
        return precision


class Scientific(Decimal):
    """
    Scientific numeral representation strings in various formats.
    """

    def __init__(self, significant=5, sign=False, times='x', thousands='',
                 shorten=True):
        """

        Parameters
        ----------
        significant: int
            {}
        signed: str, bool
            {}
        times: str
            style to use for multiplication symbol.
            * If value is either 'x' or '.' or '*':
                Symbol substitutions for unicode and latex formats are made by 
                the `unicode` and `latex` methods as per the following table:
                    unicode:    '×'         or      '·'         or      '*'
                    latex:      '\\times'   or      '\\cdot'    or      '*'
                    ascii:      'x'        or      '.'          or      '*'
            * using 'E' or 'e' will switch to E-notation style. 
                eg.: 1.3e-12 or 1.3E-12
            * Any other str may be passed in which case it will be used verbatim.
        short: bool
            Strip trailing zeros and decimal point.


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

    # __slots__ = ('times', 'base', 'exp')

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

    def __call__(self, x, times=None, base='10', exp=unicode.superscript):
        # TODO: defaults at module_level:
        # scientific notation
        # n_ = abs(x)
        m = order_of_magnitude(x)  # might be -inf
        p = self.significant

        # first get the ×10ⁿ part
        times = times or self.times
        if self.short is True:
            if (m == 0):
                times = base = ''
            if m in {0, 1}:
                exp = empty_string
            if (-m <= self.significant < 3):
                # 0.1 is shorter than 1e-1
                # 0.01 same as        1e-2  but more readable

                # nope = super().__call__(x * (10 ** -m), p)
                # this = super().__call__(x, p)
                # from IPython import embed
                # embed(header="Embedded interpreter at 'src/recipes/pprint/formatters.py':375")
                # raise ValueError()
                m = 0
                base = times = ''
                exp = empty_string
                # p = self.significant + 1

        # coefficient / mantissa / significand
        mantissa = super().__call__(x * (10 ** -m), p)  # str

        # concatenate
        return ''.join([mantissa, times, base, str(exp(m))])

    def ascii(self, x):
        return self(x, 'e', '', int)

    def unicode(self, x):
        # '\N{DECIMAL EXPONENT SYMBOL}' <-  ugly: '⏨⁵'
        # '\N{NUMBER TEN FULL STOP}'    <-  this maybe ok: "⒑⁵"
        return self(x, UNICODE_MAP.get((t := self.times), t),
                    '10',
                    unicode.superscript)

    def latex(self, x):
        return self(x, LATEX_MAP.get((t := self.times), t),
                    '10', '{{{:d}}}'.format)


class Metric:
    """
    Metric style format like "12.1 kJ" or "42.67 Gb".
    """

    def __init__(self, significant=None, base=10, unit=''):
        self.significant = significant
        self.base = int(base)
        self.unit = str(unit)

    def __call__(self, x):
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
        signed = signum(x)
        x = abs(x)
        if signed == 0:
            return str(x)

        pwr = math.log(x) / math.log(self.base)
        pwr3 = int((pwr // 3) * 3)
        sig = self.significant or [0, 1][pwr3 < 0]
        mantissa = x / (self.base ** pwr3)
        return f'{mantissa:.{sig:d}f} {METRIC_PREFIXES[pwr3]}{self.unit}'


Engineering = Metric


class Measurement(NumberBase):
    """
    A measured number with some uncertainty.
    """

    __slots__ = ('pm')

    # @api.validate()
    def __init__(self, precision: int = None, significant: int = 3,
                 signed: Union[str, bool] = '-', thousands: str = '',
                 short: bool = True, space: Union[int, tuple] = 1,
                 pm: str = '+/-'):

        if isinstance(space, int):
            space = ' ' * space

        pm = pm.join(duplicate_if_scalar(space))
        del space

        super().__init__(**locals())

    def _get_precision(self, precision, x, u):
        # decide default precision if necessary based on value of `x` and
        # uncertainty `u`.
        precision = precision or self.precision
        if (precision is None) and u is not None:
            # significant digits of measurement uncertainty determine precision
            return precision_rule_dpg(u)

        return super()._get_precision(precision, x)

    # def get_spec(self, u, precision):
    #     if u is None:
    #         return f'{self.signed}{","[:bool(self.thousands)]}.{precision}f'

    #     return f'{xr}{self.pm}{self(u, precision)}'

    def format(self, x, u, precision=None):

        xr = super().format(x, precision)

        # Right pad for when numbers are displayed to various precisions and the
        # should form a block. eg. nrs followed by a 1σ uncertainty, and we want to
        # line up with the '±'.
        # eg.:
        #   [-12   ± 1.2,
        #      1.1 ± 0.2 ]

        # if right_pad >= max(precision - n_stripped, 0):
        #     # compute required width of formatted number string
        #     m = m or order_of_magnitude(x)
        #     w = sum((int(bool(signed) & (x < 0)),
        #              max(left_pad, m + 1),  # width lhs of '.'
        #              max(right_pad, precision),  # width rhs of '.'
        #              int(precision > 0)))  # '.' expected in formatted str?

        #     s = s.ljust(w, right_pad_char)

        if u is None:
            return xr

        return f'{xr}{self.pm}{self(u, precision)}'


STD_BRACKETS = object()
STD_BRACKET_TYPES = {set: '{}',
                     list: '[]',
                     tuple: '()'}


class Collection(FormatterConstructors, SlotHelper):

    __slots__ = ('fmt', 'max_items', 'edge_items', 'sep', 'dots', 'brackets')

    def __init__(self, fmt=repr,
                 # TODO: width
                 max_items=10, edge_items=2,
                 sep=', ', dots='...', brackets=STD_BRACKETS):

        if isinstance(fmt, str):
            fmt = fmt.format
        assert callable(fmt)

        if brackets is not STD_BRACKETS:
            assert len(brackets) == 2

        kws = locals()
        kws.pop('self')
        super().__init__(**kws)

    def __call__(self, obj):
        """
        Print a pretty representation of a collection of items, trunctated
        at `max_items`.

        Parameters
        ----------
        obj
        max_items
        edge_items
        sep

        Returns
        -------

        """
        brackets = self.brackets
        if brackets is STD_BRACKETS:
            brackets = STD_BRACKET_TYPES.get(type(obj), '[]')

        if len(obj) <= self.max_items:
            return self.sep.join(map(self.fmt, obj)).join(brackets)

        return f'{self.sep}{self.dots} '.join(
            (self.sep.join(map(self.fmt, obj[:self.edge_items])),
             self.sep.join(map(self.fmt, obj[-self.edge_items:])))
        ).join(brackets)


class Array(SlotHelper):

    __slots__ = ('fmt', 'max_rows', 'max_cols', 'n_edge', 'dots', 'sep')

    def __init__(self, fmt, width=100, max_size=625, n_edge=2, dots='...',
                 sep=', '):

        # assert callable((fmt))
        kws = locals()
        kws.pop('self')
        super().__init__(**kws)

    def __call__(self, x):

        if x > self.max_size:
            return self.summarize(x)

        return vectorize(self.fmt)(x)

    def summarize(self, x):
        ''


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
        self.args = tuple(duplicate_if_scalar(test_args, 1, emit=False))
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


def oom_switch(x, log_switch):
    return abs(order_of_magnitude(x)) >= log_switch


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
                 signed='-', times='x', thousands='', short=True):
        """


        Parameters
        ----------
        log_switch: int # TODO: tuple  
            Controls switching between decimal/scientific notation. Scientific
            notation is triggered if `abs(math.log10(abs(x))) > switch`.

        short
            TODO: If short = True
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
            Scientific(significant, signed, times, thousands, short),
            Decimal(precision, significant, signed, thousands, short)
        )


class FractionOf:

    templates = dict(
        ascii=('{x}{symbol}', '{x}{symbol}/{d}'),
        unicode=('{x}{symbol}', '{x}{symbol}/{d}'),
        latex=('${x}{symbol}$', R'$\frac{{{x}{symbol}}}{{{d}}}$')
    )

    def __init__(self, symbols=(), **kws):
        symbols = {k: str(v) for k, v in dict(symbols, **kws).items()}
        assert symbols.keys() == {'ascii', 'unicode', 'latex'}
        self.symbols = dicts.AttrReadItem(symbols)

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
        x = x if ((x := f.numerator) != 1) else ""

        if ((d := f.denominator) == 1):
            return itmp.format(x=x, symbol=self.symbols[style], d=d)

        return ftmp.format(x=x, symbol=self.symbols[style], d=d)

    def format_mpl(self, f, _pos=None):
        return self.format(f, 'latex')

    def ascii(self, f, _pos=None):
        return self.format(f, 'ascii')

    def latex(self, f, _pos=None):
        return self.format(f, 'latex')  # .join('$$')

    def unicode(self, f, _pos=None):
        return self.format(f, 'unicode')


class FractionOfPi(FractionOf):
    def __init__(self):
        super().__init__(ascii='pi',
                         unicode='π',
                         latex=R'\pi')

    def from_radian(self, x, _pos=None, style='latex'):
        return self.format(x / math.pi, style)


def frac_of(f, symbol, i_template='{x}{symbol}', f_template='{x}{symbol}/{d}'):
    # i_template='{x}{symbol}', f_

    if f == 0:
        return '0'

    if f == 1:
        return symbol

    f = f.limit_denominator()
    x = x if ((x := f.numerator) != 1) else ""

    if ((d := f.denominator) == 1):
        return i_template.format(x=x, symbol=symbol)

    return f_template.format(x=x, symbol=symbol, d=d)

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
