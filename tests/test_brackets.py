
# third-party libs
import pytest

# local libs
from recipes import op
from recipes.functionals import negate
from recipes.testing import Expect, Throws, mock, expected
from recipes.string.brackets import match, remove, outermost, braces, xsplit


# @pytest.mark.skip()
@expected(
    {('hello(world)', '()'):                 'world',
     ('unclosed((((((', '()'):               None,
     ('nested((([inside]))]]])))', '[]'):    'inside',
     ('<s>', '<>'):                          's',
     ('((())', '()'):                        None})
def test_match_brackets(s, pair, result):
    r, (i, j) = match(s, pair)
    assert r == result
    if r:
        assert r == s[i+1:j]


test_brackets_must_close = Expect(match)({
    #
    mock('foo{bla', '{}', must_close=False):           (None, (None, None)),
    mock('open((((((', '()', must_close=False):        (None, (None, None)),
    mock('((())', '()', must_close=False):             (None, (None, None)),
    # #
    mock('foo{bla', '{}', must_close=-1):           ('bla', (3, None)),
    mock('open((((((', '()', must_close=-1):        ('(((((', (4, None)),
    mock('((())', '()', must_close=-1):             ('(())', (0, None)),
    #
    mock('(', '()', must_close=True):               Throws(ValueError),
    mock('also_open((((((', '()', must_close=True): Throws(ValueError),
    mock('((())', '()', must_close=True):           Throws(ValueError)
})
# pytest.mark.skip(test_brackets_must_close)


test_iter = Expect(braces.iter)(
    {'{}{}{}{}': [('', (0, 1)), ('', (2, 3)), ('', (4, 5)), ('', (6, 7))]},
    transform=list
)


@pytest.mark.parametrize('string', ['0{2{4,6,8}{}{3,5{{{9}}}}}'])
def test_iter_nested(string):
    for b, (i, j) in braces.iter_nested(string):
        assert b == string[i+1:j]


test_unbracket = Expect(remove)({
    mock.remove('', '()'):                             '',
    mock.remove('()', '()'):                           '',
    mock.remove('test()', '()'):                       'test',
    mock.remove('test(())', '()'):                     'test',
    mock.remove('test(()', '()'):                      'test(()',
    mock.remove('{[(foo)]}', '()'):                    '{[foo]}',
    mock.remove('{{{hello world!}}}', '{}'):           'hello world!',
    mock.remove('{some,thing}{}', '{}',
                condition=op.contained(',').within):
    'some,thing{}',
    mock.remove('{some,thing}{}', '{}',
                condition=negate(op.contained(',').within)):     '{some,thing}',
    mock.remove('{{1}}', '{}', 0):                     '{{1}}',
    mock.remove('{{1}}', '{}', 1):                     '{1}',
    mock.remove('{{hi{} {x}}}', '{}',
                condition=outermost):               'hi{} {x}',
    mock.remove('((hello) world)', '()',
                condition=outermost):               '(hello) world',
    mock.remove('{{Bai}, Yu and {Liu}, JiFeng}', '{}'):
    'Bai, Yu and Liu, JiFeng'
})
# pytest.mark.skip(test_unbracket)

# test splitter
test_split = Expect(braces.split2)(
    {'':                    [('', '')],
     '...':                 [('...', '')],
     '{}':                  [('', '{}')],
     'x{}':                 [('x', '{}')],
     'x{}x':                [('x', '{}'), ('x', '')],
     '{}{}{}{}':            [('', '{}'), ('', '{}'), ('', '{}'), ('', '{}')],
     'ch{1,2,{4..6}}...{,},xxx':
        [('ch', '{1,2,{4..6}}'), ('...', '{,}'), (',xxx', '')],

     },
    transform=list)

test_xsplit = Expect(xsplit)(
    {'':                    [''],
     '...':                 ['...'],
     '{4..6}':              ['{4..6}'],
     '{{4,6}}':             ['{{4,6}}'],
     '{}{}{}{}':            ['{}{}{}{}'],
     'a,b':                 ['a', 'b'],
     'ch{1,2,{4..6}}...{}': ['ch{1,2,{4..6}}...{}'],
     'a,b,c{d,e{f,g}}':     ['a', 'b', 'c{d,e{f,g}}']
     },
    transform=list)


test_depth = Expect(braces.depth)({
    '{}':                                   1,
    '':                                     0,
    '{{{{{}}}}}':                           5,
    '{{{{{99dmckkcmmm/ {}}}}}}':            6,
    '{{{{{99dmckkcmmm/ {}{}}}}}{}}':        6
})
