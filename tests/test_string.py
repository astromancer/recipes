from recipes.testing import Expect, mock
from recipes.string import match_brackets, Percentage, replace, unbracket
import pytest


test_replace = Expect(replace)(
    {  # basic
        mock.replace('hello world', {'h': 'm', 'o ': 'ow '}):
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
        mock.replace('hello world', dict(h ='m', o='ow', rld='', w='v')):
        'mellow vow'
    }
)


# @pytest.mark.skip()
@pytest.mark.parametrize('s, brackets, result',
                         [('hello(world)', '()', 'world'),
                          ('unclosed((((((', '()', None),
                          ('nested((([inside]))]]])))', '[]', 'inside'),
                          ('<s>', '<>', 's'),
                          ('((())', '()', None)])
def test_match_brackets(s, brackets, result):
    r, (i, j) = match_brackets(s, brackets)
    assert r == result
    if r:
        assert r == s[i+1:j]


# @pytest.mark.skip()
@pytest.mark.parametrize('s, b, e',
                         [('foo{bla', '{}', 'bla'),
                          ('open((((((', '()', '((((('),
                          ('((())', '()', '(())')])
def test_brackets_must_close(s, b, e):
    sub, (_, j) = match_brackets(s, b, must_close=-1)
    assert sub == e
    assert j is None


@pytest.mark.parametrize('s', ['(', 'also_open((((((', '((())'])
def test_brackets_must_close_raises(s):
    with pytest.raises(ValueError):
        match_brackets(s, must_close=True)


test_unbracket = Expect(unbracket)(
    {mock.unbracket(''):                                '',
     mock.unbracket('()'):                              '',
     mock.unbracket('test()'):                          'test',
     mock.unbracket('test(())'):                        'test',
     mock.unbracket('test(()'):                         'test(()',
     mock.unbracket('{[(foo)]}'):                       '{[foo]}',
     mock.unbracket('{{{hello world!}}}', '{}'):        'hello world!',
     mock.unbracket('{some,thing}', '{}',
                    condition=lambda x: ',' not in x):  '{some,thing}'  # SAME
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


@pytest.mark.parametrize('s, e', [('20%', 2469),
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
