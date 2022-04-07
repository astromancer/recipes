# pylint: disable=all
# third-party
import pytest

# local
from recipes import op
from recipes.functionals import negate
from recipes.testing import Expected, Throws, mock, expected
from recipes.string.brackets import (match, remove, Condition, level, braces,
                                     csplit, BracketPair, is_outer)


# @pytest.mark.skip()
@expected(
    {('hello(world)', '()'):                 'world',
     ('unclosed((((((', '()'):               None,
     ('nested((([inside]))]]])))', '[]'):    'inside',
     ('<s>', '<>'):                          's',
     ('((())', '()'):                        None})
def test_match_brackets(string, pair, expected):
    m = match(string, pair)
    r = m.enclosed
    assert r == expected
    if r:
        i, j = m.indices
        assert r == string[i+1:j]


test_brackets_must_close = Expected(match)({
    #
    mock('foo{bla', '{}', must_close=False):     BracketPair('{}', None, (None, None)),
    mock('open((((((', '()', must_close=False):  BracketPair('()', None, (None, None)),
    mock('((())', '()', must_close=False):       BracketPair('()', None, (None, None)),
    # #
    mock('foo{bla', '{}', must_close=-1):           BracketPair('{}', 'bla', (3, None)),
    mock('open((((((', '()', must_close=-1):        BracketPair('()', '(((((', (4, None)),
    mock('((())', '()', must_close=-1):             BracketPair('()', '(())', (0, None)),
    #
    mock('(', '()', must_close=True):               Throws(ValueError),
    mock('also_open((((((', '()', must_close=True): Throws(ValueError),
    mock('((())', '()', must_close=True):           Throws(ValueError)
})
# pytest.mark.skip(test_brackets_must_close)


test_iter = Expected(braces.iter)(
    {'{}{}{}{}':
        [BracketPair('{}', '', (0, 1)),
         BracketPair('{}', '', (2, 3)),
         BracketPair('{}', '', (4, 5)),
         BracketPair('{}', '', (6, 7))]},
    transform=list
)


class Test_iterate:
    @pytest.mark.parametrize('string', ['0{2{4,6,8}{}{3,5{{{9}}}}}'])
    def test_iterate(self, string):
        for b, (i, j), _lvl in braces.iterate(string):
            assert b == string[i+1:j]

    @pytest.mark.parametrize('depth', range(7))
    def test_depth_filter(self, depth):
        itr = braces.iterate('0{1{2{3{4{5{6{7}}}}}}}', condition=(level == depth))
        pair = next(itr)
        assert pair.level == depth
        assert pair.enclosed[0] == str(depth + 1)


has_comma = op.has(',').within
test_unbracket = Expected(remove)({
    mock.remove('', '()'):                                      '',
    mock.remove('()', '()'):                                    '',
    mock.remove('test()', '()'):                                'test',
    mock.remove('test(())', '()'):                              'test',
    mock.remove('test(()', '()'):                               'test(()',
    mock.remove('{[(foo)]}', '()'):                             '{[foo]}',
    mock.remove('{{{hello world!}}}', '{}'):                    'hello world!',
    mock.remove('{some,thing}{}', '{}',
                Condition(enclosed=has_comma)):                 'some,thing{}',
    mock.remove('{some,thing}{}', '{}',
                Condition(enclosed=negate(has_comma))):         '{some,thing}',
    mock.remove('{{1}}', '{}', level < 0):                        '{{1}}',
    mock.remove('{{1}}', '{}', level == 1):                       '{1}',
    mock.remove('{{hi{} {x}}}', '{}', level == 0):                '{hi{} {x}}',
    mock.remove('{{hi{} {x}}}', '{}', is_outer):                 'hi{} {x}',
    mock.remove('((hello) world)', '()', level == 0):             '(hello) world',
    mock.remove('((hello) world)', '()', is_outer):              '(hello) world',
    mock.remove('{{Bai}, Yu and {Liu}, JiFeng}', '{}'):
    'Bai, Yu and Liu, JiFeng'
})
# pytest.mark.skip(test_unbracket)

# test splitter
test_split = Expected(braces.split2)(
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

test_csplit = Expected(csplit)(
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


test_depth = Expected(braces.depth)({
    '{}':                                   1,
    '':                                     0,
    '{{{{{}}}}}':                           5,
    '{{{{{99dmckkcmmm/ {}}}}}}':            6,
    '{{{{{99dmckkcmmm/ {}{}}}}}{}}':        6
})

def test_new_parser():
    BracketParser()._index('[this(nested{set<of>[brackets]})]')