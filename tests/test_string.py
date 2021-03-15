from recipes.testing import Expect, Throws, mock, expected
from recipes.string import Percentage, sub
import pytest



test_sub = Expect(sub)(
    # basic
    {mock.sub('hello world', {'h': 'm', 'o ': 'ow '}):
     'mellow world',
     mock.sub('hello world', dict(h='m', o='ow', rld='')):
     'mellow wow',
     mock.sub('hello world', {'h': 'm', 'o ': 'ow ', 'l': ''}):
     'meow word',
     mock.sub('hello world', dict(hell='lo', wo='', r='ro', d='l')):
     'loo roll',
     # character permutations
     mock.sub('option(A, B)', {'B': 'A', 'A': 'B'}):
     'option(B, A)',
     mock.sub('AABBCC', {'A': 'B', 'B': 'C', 'C': 'c'}):
     'BBCCcc',
     mock.sub('hello world', dict(h='m', o='ow', rld='', w='v')):
     'mellow vow'
     }
)


# @pytest.mark.skip()
@expected(
    {mock('hello(world)', '()'):                 'world',
     mock('unclosed((((((', '()'):               None,
     mock('nested((([inside]))]]])))', '[]'):    'inside',
     mock('<s>', '<>'):                          's',
     mock('((())', '()'):                        None})
def test_match_brackets(s, brackets, result):
    r, (i, j) = match_brackets(s, brackets)
    assert r == result
    if r:
        assert r == s[i+1:j]


test_brackets_must_close = Expect(match_brackets)(
    {mock('foo{bla', '{}'):                     ('bla', (3, None)),
     mock('open(((((('):                        ('(((((', (4, None)),
     mock('((())'):                             ('(())', (1, None)),
     mock('(', must_close=True):                Throws(ValueError),
     mock('also_open((((((', must_close=True):  Throws(ValueError),
     mock('((())', must_close=True):            Throws(ValueError)}
)
# '(',
#          'also_open((((((',
#          '((())']


# def test_brackets_must_close(s, b, e):
#     sub, (_, j) = match_brackets(s, b, must_close=-1)
#     assert sub == e
#     assert j is None

# @pytest.mark.skip()
# @pytest.mark.parametrize(
#     's, b, e',
#     [('foo{bla', '{}', 'bla'),
#      ('open((((((', '()', '((((('),
#      ('((())', '()', '(())')])
# def test_brackets_must_close(s, b, e):
#     sub, (_, j) = match_brackets(s, b, must_close=-1)
#     assert sub == e
#     assert j is None

# DEPRECATED
# test_brackets_must_close_raises = \
#     ExpectFailure(match_brackets, must_close=True)(
#         ['(',
#          'also_open((((((',
#          '((())']
#     )

# test_brackets_must_close = Expect(match_brackets, must_close=True)(
#     {'(':                   Throws(ValueError),
#      'also_open((((((':     Throws(ValueError),
#      '((())':               Throws(ValueError)}
# )

# @pytest.mark.parametrize('s', ['(', 'also_open((((((', '((())'])
# def test_brackets_must_close_raises(s):
#     with pytest.raises(ValueError):
#         match_brackets(s, must_close=True)


test_unbracket = Expect(unbracket)(
    {mock.unbracket(''):                                '',
     mock.unbracket('()'):                              '',
     mock.unbracket('test()'):                          'test',
     mock.unbracket('test(())'):                        'test',
     mock.unbracket('test(()'):                         'test(()',
     mock.unbracket('{[(foo)]}'):                       '{[foo]}',
     mock.unbracket('{{{hello world!}}}', '{}'):        'hello world!',
     mock.unbracket('{some,thing}{}', '{}', 
                    condition=contained(',').within):
                                                        'some,thing{}',
     mock('{some,thing}{}', '{}', 
          condition=negate(contained(',').within)):     '{some,thing}',                                                 
     mock.unbracket('{{1}}', '{}', 0):                  '{{1}}',
     mock.unbracket('{{1}}', '{}', 1):                  '{1}',
     mock.unbracket('{{hi{} {x}}}', '{}',
                    condition=outermost):                'hi{} {x}',
     mock.unbracket('((hello) world)',
                    condition=outermost):          '(hello) world'
     }
)

# _unbracket('{{{hello world!}}}', '{}', condition=lambda x: '!' not in x)
# Out[53]: '{{{hello world!}}}'

# _unbracket('{{{hello world? {this my jam!}}}', '{}', condition=lambda x: '!' not in x)
# Out[54]: '{{{hello world? {this my jam!}}}'


# tests = ['root/{ch{{1,2},{4..6}},main{1,2},{1,2}test}*.png',
#      ...:          'ch{{1,2},{4..6}},main{1,2},{1,2}test']
#      ...: lists(map(bash.fucksplitter, tests))

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
