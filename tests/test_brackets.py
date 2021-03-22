import pytest
from recipes.testing import Expect, Throws, mock, expected
from recipes.string.brackets import match, remove, outermost, contained
from recipes.functionals import negate


@pytest.mark.skip()
@expected(
    {mock('hello(world)', '()'):                 'world',
     mock('unclosed((((((', '()'):               None,
     mock('nested((([inside]))]]])))', '[]'):    'inside',
     mock('<s>', '<>'):                          's',
     mock('((())', '()'):                        None})
def test_match_brackets(s, pair, result):
    r, (i, j) = match(s, pair)
    assert r == result
    if r:
        assert r == s[i+1:j]


test_brackets_must_close = Expect(match)(
    {
        # mock('foo{bla', '{}'):                          ('bla', (3, None)),
        # mock('open((((((', '()'):                       ('(((((', (4, None)),
        # mock('((())', '()'):                            ('(())', (1, None)),
        mock('(', '()', must_close=True):               Throws(ValueError),
        mock('also_open((((((', '()', must_close=True): Throws(ValueError),
        mock('((())', '()', must_close=True):           Throws(ValueError)
    }
)
# pytest.mark.skip(test_brackets_must_close)


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


test_unbracket = Expect(remove)(
    {mock.remove('', '()'):                             '',
     mock.remove('()', '()'):                           '',
     mock.remove('test()', '()'):                       'test',
     mock.remove('test(())', '()'):                     'test',
     mock.remove('test(()', '()'):                      'test(()',
     mock.remove('{[(foo)]}', '()'):                    '{[foo]}',
     mock.remove('{{{hello world!}}}', '{}'):           'hello world!',
     mock.remove('{some,thing}{}', '{}',
                 condition=contained(',').within):
     'some,thing{}',
     mock.remove('{some,thing}{}', '{}',
                 condition=negate(contained(',').within)):     '{some,thing}',
     mock.remove('{{1}}', '{}', 0):                     '{{1}}',
     mock.remove('{{1}}', '{}', 1):                     '{1}',
     mock.remove('{{hi{} {x}}}', '{}',
                 condition=outermost):               'hi{} {x}',
     mock.remove('((hello) world)', '()',
                 condition=outermost):               '(hello) world',
     mock.remove('{{Bai}, Yu and {Liu}, JiFeng}', '{}'):
         'Bai, Yu and Liu, JiFeng'
     }
)
pytest.mark.skip(test_unbracket)
