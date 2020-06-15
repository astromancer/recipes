# test padding
import random

from recipes.pprint.nrs import decimal, hms, to_sexagesimal
# leading_decimal_zeros

import numpy as np

# assert leading_decimal_zeros(0.0001) == 3
# assert leading_decimal_zeros(1000.0001) == 3
# assert leading_decimal_zeros(12e-23) == 21

[hms(1e4),
 hms(1.333121112e2, 5),
 hms(1.333121112e2, 5, ':'),
 hms(1.333121112e2, 5, short=False),
 hms(1.333121112e2, 'm', short=False, unicode=True)]


# ['02h46m40.0s',
#  '00h02m13.31211s',
#  '00:02:13.31211',
#  '00h02m13.31211s',
#  '00ʰ02ᵐ']

def test_hms_convert(n, base_unit, precision):
    sexa = to_sexagesimal(n, base_unit, precision)
    assert to_sec(sexa) == n


def to_sec(sexa, base_unit, precision):
    # FIXME;  not quite right
    pwr = np.arange(3)[::-1]['hms'.index(base_unit):'hms'.index(precision) + 1]
    return np.multiply(sexa, np.power(60, pwr)).sum()


def test_decimal():
    assert decimal(3.14159265, 5) == '3.14159'
    assert decimal(2.0000001, 3, compact=True) == '2'
    assert decimal(2.01000001, 1, compact=True) == '2'
    assert decimal(2.01000001, 2, compact=True) == '2.01'

    assert decimal(1.233, left_pad=5) == '    1.23'


def test_padding(s, precision=6):
    for i in range(10):
        l = random.randrange(0, 10)
        r = random.randrange(0, 10)
        s = decimal(s, precision=precision, left_pad=l, right_pad=r)
        i, d, e = s.partition('.')
        assert len(i) >= l, f'{len(i)} < {l}'
        assert len(e) == max(r, p), f'{len(e)} ≠ max({r}, {p + 1})'


test_padding(-40.548522)
test_padding(40.548522)
