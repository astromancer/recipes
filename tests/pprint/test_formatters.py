

# std
import itertools as itt

# third-party
import numpy

# local
from recipes.pprint.formatters import Decimal


if __name__ == '__main__':

    styles = Decimal,  # Scientific,  # , Metric
    formats = 'ascii', 'unicode', 'latex'
    cases = (0, 0.000123456789, 1.123456789, 1234.56789, 123456789.01, 0.1001)
    significant = (1, 2, 3)
    shorten = (True, ' ', False)
    multi = ('x', '.')

    for kls in styles:
        for fmt, sig, short, nr in itt.product(formats, significant, shorten, cases):
            obj = kls(sig, short=short)
            print(f'{obj}.{fmt}({nr})')
            # print(fmt, sig, short, nr)
            print(repr(getattr(obj, fmt)(nr)), '\n')
            # break

    # for times in (multi if kls is Scientific else ['']):
        # spec = dict(short=short)
        # if times:
        #     spec['times'] = times
        # print(kls.__name__, fmt, spec)
        # print('|'.join((' ' * 5, *map('{: >20}'.format, map(str, cases)))))
        # for p in precision:
        #     # print(kls.__name__, n, p)

        #     row = []
        #     for n in cases:
        #         try:
        #             s = getattr(kls(p, **spec), fmt)(n)
        #         except Exception as err:
        #             raise
        #             s = 'xxx'
        #         row.append(f'{s: >20}')

        #     print('|'.join((f'p = {p}', *row)))
        # print()


# #
# test_decimal = Expected(decimal)(
#     {mock.decimal(1e4):                         '10000.0',
#      mock.decimal(0.0000123444):                '0.0000123',
#      mock.decimal(3.14159265, 5):               '3.14159',
#      mock.decimal(2.0000001, 3, short=True):    '2',
#      mock.decimal(2.01000001, 1, short=True):   '2',
#      mock.decimal(2.01000001, 2, short=True):   '2.01',
#      #  mock.decimal(1.233, pad=5):             '       1.23'
#      }
# )
