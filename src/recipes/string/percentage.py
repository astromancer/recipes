"""
Recognise and compute with percentages in strings.
"""


# std
import re
import numbers
from collections import abc

# third-party
import numpy as np


# ---------------------------------------------------------------------------- #
REGEX = re.compile(R'([\d.,]+)\s*%')


# ---------------------------------------------------------------------------- #

class Percentage:
    """
    An object representing a percentage of something (usually a number) that
    computes the actual percentage value when called.
    """

    # TODO: `__mul__` etc

    __slots__ = ('frac')

    def __init__(self, string):
        """
        Convert a percentage string like '3.23494%' to a floating point number
        and retrieve the actual number (percentage of a total) that it
        represents

        Parameters
        ----------
        s : str The string representing the percentage, eg: '3%', '12.0001 %'

        Examples
        --------
        >>> Percentage('1.25%').of(12345)
        154.3125

        Raises
        ------
        ValueError
            If percentage could not be parsed from the string.
        """
        if (mo := REGEX.search(string)) is None:
            raise ValueError(f'Could not find anything resembling a percentage'
                             f' in the string {string!r}.')

        self.frac = float(mo.group(1)) / 100

    def __repr__(self):
        return f'{type(self).__name__}({self.frac:.2%})'

    def __str__(self):
        return f'{self.frac:.2%}'

    def __format__(self, format_spec):
        return self.frac.format(format_spec)

    def __call__(self, number):
        return self.of(n)

    def of(self, total):
        """
        Get the number representing by the percentage as a total. Basically just
        multiplies the parsed fraction with the number `total`.

        Parameters
        ----------
        total : number, array-like
            Any number.

        Returns
        -------
        float or np.ndarray
        """
        try:
            if isinstance(number, numbers.Real):
                return self.frac * number

            if isinstance(number, abc.Collection):
                return self.frac * np.asanyarray(number, float)

        except ValueError:
            raise TypeError('Not a valid number or numeric array type.') \
                from None
