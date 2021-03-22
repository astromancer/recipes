from recipes.testing import Expect, Throws, mock, expected
from recipes.string import Percentage, replace, title
import pytest



test_replace = Expect(replace)(
    # basic
    {mock.replace('hello world', {'h': 'm', 'o ': 'ow '}):
     'mellow world',
     mock.replace('hello world', dict(h='m', o='ow', rld='')):
     'mellow wow',
     mock.replace('hello world', {'h': 'm', 'o ': 'ow ', 'l': ''}):
     'meow word',
     mock.replace('hello world', dict(hell='lo', wo='', r='ro', d='l')):
     'loo roll',
     # character permutations
     mock.replace('option(A, B)', {'B': 'A', 'A': 'B'}):
     'option(B, A)',
     mock.replace('AABBCC', {'A': 'B', 'B': 'C', 'C': 'c'}):
     'BBCCcc',
     mock.replace('hello world', dict(h='m', o='ow', rld='', w='v')):
     'mellow vow'
     }
)


test_replace = Expect(title)(
    # basic
    {mock.title('hello world'):             'Hello World',
     mock.title('hello world', 'world'):    'Hello world',
     mock.title('internal in inside', 'in'):   'Internal in Inside',
     mock.title('words for the win', ('for', 'the')): 'Words for the Win'
     }
)


# _unbracket('{{{hello world!}}}', '{}', condition=lambda x: '!' not in x)
# Out[53]: '{{{hello world!}}}'

# _unbracket('{{{hello world? {this my jam!}}}', '{}', condition=lambda x: '!' not in x)
# Out[54]: '{{{hello world? {this my jam!}}}'


# tests = ['root/{ch{{1,2},{4..6}},main{1,2},{1,2}test}*.png',
#      ...:          'ch{{1,2},{4..6}},main{1,2},{1,2}test']
#      ...: lists(map(bash.splitter, tests))

# [['root/{ch{{1,2},{4..6}},main{1,2},{1,2}test}*.png'],
#  ['ch{{1,2},{4..6}}', 'main{1,2}', '{1,2}test']]


@ pytest.mark.parametrize('s, e', [('20%', 2469),
                                   ('100.01%', 12346.2345),
                                   ('12.0001 %', 1481.412345)])
def test_percentage(s, e):
    assert Percentage(s).of(12345.) == e


# @pytest.mark.parametrize('s', ['3r',
#                                'some text 100.0.ss',
#                                '12.0001 %'])
# def test_percentage_raises(s):
#     n = Percentage(s).of(12345.)
#     print(n)
