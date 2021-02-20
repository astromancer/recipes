

import random

from recipes.pprint.nrs import decimal, hms, to_sexagesimal
# leading_decimal_zeros
import pytest
import numpy as np


from recipes.testing import Expect, mock

#
test_decimal = Expect(decimal)(
    {mock.decimal(1e4):                         '10000.0',
     mock.decimal(0.0000123444):                '0.0000123',
     mock.decimal(3.14159265, 5):               '3.14159',
     mock.decimal(2.0000001, 3, short=True):    '2',
     mock.decimal(2.01000001, 1, short=True):   '2',
     mock.decimal(2.01000001, 2, short=True):   '2.01',
     #  mock.decimal(1.233, pad=5):             '       1.23'
     }
)


test_hms = Expect(hms)(
    {mock.hms(1e4):                             '02h46m40.0s',
     mock.hms(1.333121112e2, 5):                '00h02m13.31211s',
     mock.hms(1.333121112e2, 5, ':'):           '00:02:13.31211',
     mock.hms(1.333121112e2, 5, short=False):   '00h02m13.31211s',
     mock.hms(1.333121112e2, 'm0',  
              short=False, unicode=True):       '00ʰ02ᵐ',
     mock.hms(119.95, 's0'):                    '00h02m00s',
     mock.hms(1000, 'm0', sep=':'):             '00:17',
     #  ex.hms(1e4, sep='', sig=0, sign='+'):  '024640'
     }
)


@pytest.mark.skip()
def test_hms_convert(n, base_unit, precision):
    sexa = to_sexagesimal(n, base_unit, precision)
    assert to_sec(sexa) == n


def to_sec(sexa, base_unit, precision):
    # FIXME;  not quite right
    pwr = np.arange(3)[::-1]['hms'.index(base_unit):'hms'.index(precision) + 1]
    return np.multiply(sexa, np.power(60, pwr)).sum()

# assert leading_decimal_zeros(0.0001) == 3
# assert leading_decimal_zeros(1000.0001) == 3
# assert leading_decimal_zeros(12e-23) == 21


# test padding
@pytest.mark.skip()
def test_padding(n, p=6):
    for i in range(10):
        l = random.randrange(0, 10)
        r = random.randrange(0, 10)
        s = pad(str(n), precision=p, left_pad=l, right_pad=r)
        i, d, e = s.partition('.')
        assert len(i) >= l, f'{len(i)} < {l}'
        assert len(e) == max(r, p), f'{len(e)} ≠ max({r}, {p + 1})'


# test_padding(-40.548522)
# test_padding(40.548522)
