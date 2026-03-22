# pylint: disable=all

# third-party
import pytest

# local
from recipes import op
from recipes.functionals import negate
from recipes.testing import Expected, Throws, expected, mock
from recipes.string.delimited import (
    Condition,
    Match,
    Parser,
    braces,
    csplit,
    is_outer,
    level,
    match,
    remove,
    _multi_index,
)


# # with ApiMocker(_multi_index, right_transform=tuple) as _multi_index:
@expected(
    {
        ('hello(world)', '()'): ((5, '('), (11, ')')),
        ('unclosed((((((', '()'): (
            (8, '('),
            (9, '('),
            (10, '('),
            (11, '('),
            (12, '('),
            (13, '('),
        ),
        ('nested((([inside]))]]])))', '[]'): (
            (9, '['),
            (16, ']'),
            (19, ']'),
            (20, ']'),
            (21, ']'),
        ),
        ('<s>', '<>'): ((0, '<'), (2, '>')),
        ('((())', '()'): (
            (0, '('),
            (1, '('),
            (2, '('),
            (3, ')'),
            (4, ')'),
        ),
        ('"{TEXT}"', '""'): ((0, '"'), (7, '"')),
        (
            r"""(?xsm)                        # verbose, dotall (. _multi_indexes newline)
                (?P<pre>                           # preceeding content
                    ^\s*                           #   whitespace
                    [^#'"\n]*?                     #   not comment and not opening quote
                )
                (?P<marks>(?i:(?:[rf]|[rb]){0,2})) # string class indicator
                (?P<quote>                         # quote characters
                    (?P<q>['"]){1}(?:(?P=q){2})?   #   single or triple quote
                )
                (?P<content>.*?)                   # string contents
                (?<!\\)                            # ignore escaped quotes \' \"
                (?P=quote)                         # closing quote
                (?P<post>[^\n]*)                   # any trailing code up to newline
                """,
            ('(?P', ')'),
        ): (
            (5, ')'),
            (73, ')'),
            (91, '(?P'),
            (318, ')'),
            (336, '(?P'),
            (362, ')'),
            (368, ')'),
            (369, ')'),
            (412, '(?P'),
            (486, '(?P'),
            (496, ')'),
            (503, '(?P'),
            (508, ')'),
            (512, ')'),
            (560, ')'),
            (578, '(?P'),
            (593, ')'),
            (653, ')'),
            (728, '(?P'),
            (737, ')'),
            (795, '(?P'),
            (810, ')')
        ),
        (' "hello world!" ', '""'): ((1, '"') != (14, '"')),
    },
)
def test_multi_index(string, delimiters, expected):
    assert tuple(_multi_index(string, delimiters)) == expected


# @pytest.mark.skip()
@expected(
    {
        ('hello(world)', '()'): 'world',
        ('unclosed((((((', '()'): None,
        ('nested((([inside]))]]])))', '[]'): 'inside',
        ('<s>', '<>'): 's',
        ('((())', '()'): None,
        ('"{TEXT}"', '""'): '{TEXT}',
        (
            r"""(?xsm)                        # verbose, dotall (. matches newline)
            (?P<pre>                           # preceeding content
                ^\s*                           #   whitespace
                [^#'"\n]*?                     #   not comment and not opening quote
            )
            (?P<marks>(?i:(?:[rf]|[rb]){0,2})) # string class indicator
            (?P<quote>                         # quote characters
                (?P<q>['"]){1}(?:(?P=q){2})?   #   single or triple quote
            )
            (?P<content>.*?)                   # string contents
            (?<!\\)                            # ignore escaped quotes \' \"
            (?P=quote)                         # closing quote
            (?P<post>[^\n]*)                   # any trailing code up to newline
         """,
            ('(?P', ')'),
        ): r"""<pre>                          # preceeding content
            ^\s*                           #   whitespace
            [^#'"\n]*?                     #   not comment and not opening quote
        """,
        (' "hello world!" ', '""'): 'hello world!',
    }
)
def test_match(string, pair, expected):
    m = match(string, pair)
    r = m.enclosed
    assert r == expected
    if r:
        i, j = m.indices
        assert r == string[i + 1: j]


test_delimiters_must_close = Expected(match)(
    {
        #
        mock('open((((((', '()', must_close=0): Match('()', None, (4, None)),
        mock('((())', '()', must_close=0): Match('()', None, (0, None)),
        #
        mock('foo{bla', '{}', must_close=0): Match('{}', None, (3, None)),
        mock('foo{bla', '{}', must_close=-1): None,
        mock('open((((((', '()', must_close=0): Match('()', None, (4, None)),
        mock('open((((((', '()', must_close=-1): None,
        mock('open((((((', '()', must_close=1): Throws(ValueError),
        mock('((())', '()', must_close=0): Match('()', None, (0, None)),
        # mock('((())', '()', must_close=-1):      Match('()', '', (2, 3), level=2),
        mock('((())', '()', must_close=1): Throws(ValueError),
        #
        mock('(', '()', must_close=1): Throws(ValueError),
    }
)
# pytest.mark.skip(test_delimiters_must_close)


test_iter = Expected(braces.iterate)(
    {
        '{}{}{}{}': [
            Match('{}', '', (0, 1)),
            Match('{}', '', (2, 3)),
            Match('{}', '', (4, 5)),
            Match('{}', '', (6, 7)),
        ]
    },
    transform=list,
)


class TestIterate:
    cases = {
        ('hello(world)', '()'): [
            Match(
                delimiters=('(', ')'),
                enclosed='world',
                indices=(5, 11),
                level=0,
            )
        ],
        ('unclosed((((((', '()'): [],
        ('nested((([inside]))]]])))', '[]'): [
            Match(
                delimiters=('[', ']'),
                enclosed='inside',
                indices=(9, 16),
                level=0,
            )
        ],
        ('0{2{4,6,8}{}{3,5{{{9}}}}}', '{}'): [
            Match(
                delimiters=('{', '}'), enclosed='4,6,8', indices=(3, 9), level=1
            ),
            Match(
                delimiters=('{', '}'), enclosed='', indices=(10, 11), level=1
            ),
            Match(
                delimiters=('{', '}'), enclosed='9', indices=(18, 20), level=4
            ),
            Match(
                delimiters=('{', '}'), enclosed='{9}', indices=(17, 21), level=3
            ),
            Match(
                delimiters=('{', '}'),
                enclosed='{{9}}',
                indices=(16, 22),
                level=2,
            ),
            Match(
                delimiters=('{', '}'),
                enclosed='3,5{{{9}}}',
                indices=(12, 23),
                level=1,
            ),
            Match(
                delimiters=('{', '}'),
                enclosed='2{4,6,8}{}{3,5{{{9}}}}',
                indices=(1, 24),
                level=0,
            ),
        ],
        ('<s>', '<>'): [
            Match(delimiters=('<', '>'), enclosed='s', indices=(0, 2), level=0)
        ],
        ('((())', '()'): [
            Match(delimiters=('(', ')'), enclosed='', indices=(2, 3), level=2),
            Match(
                delimiters=('(', ')'), enclosed='()', indices=(1, 4), level=1
            ),
        ],
        ('"{TEXT}"', '""'): [
            Match(
                delimiters=('"', '"'),
                enclosed='{TEXT}',
                indices=(0, 7),
                level=0,
            )
        ],
        (
            r"""(?xsm)                        # verbose, dotall (. matches newline)
            (?P<pre>                           # preceeding content
                ^\s*                           #   whitespace
                [^#'"\n]*?                     #   not comment and not opening quote
            )
            (?P<marks>(?i:(?:[rf]|[rb]){0,2})) # string class indicator
            (?P<quote>                         # quote characters
                (?P<q>['"]){1}(?:(?P=q){2})?   #   single or triple quote
            )
            (?P<content>.*?)                   # string contents
            (?<!\\)                            # ignore escaped quotes \' \"
            (?P=quote)                         # closing quote
            (?P<post>[^\n]*)                   # any trailing code up to newline
         """,
            ('(?P', ')'),
        ): [
            Match(
                delimiters=('(?P', ')'),
                enclosed='<pre>                           # preceeding content\n'
                '                ^\\s*                           '
                '#   whitespace\n'
                '                [^#\'"\\n]*?                     '
                '#   not comment and not opening quote\n            ',
                indices=(80, 295),
                level=0,
            ),
            Match(
                delimiters=('(?P', ')'),
                enclosed='<marks>(?i:(?:[rf]|[rb]',
                indices=(309, 335),
                level=0,
            ),
            Match(
                delimiters=('(?P', ')'),
                enclosed='<q>[\'"]',
                indices=(451, 461),
                level=1,
            ),
            Match(
                delimiters=('(?P', ')'),
                enclosed='=q',
                indices=(468, 473),
                level=1,
            ),
            Match(
                delimiters=('(?P', ')'),
                enclosed='<quote>                         # quote characters\n'
                '                (?P<q>[\'"]){1}(?:(?P=q){2}',
                indices=(381, 477),
                level=0,
            ),
            Match(
                delimiters=('(?P', ')'),
                enclosed='<content>.*?',
                indices=(535, 550),
                level=0
            ),
            Match(
                delimiters=('(?P', ')'),
                enclosed='=quote',
                indices=(677, 686),
                level=0,
            ),
            Match(
                delimiters=('(?P', ')'),
                enclosed='<post>[^\\n]*',
                indices=(740, 755),
                level=0,
            ),
        ],
        (' "hello world!" ', '""'): [
            Match(
                delimiters=('"', '"'),
                enclosed='hello world!',
                indices=(1, 14),
                level=0,
            )
        ],
    }

    # @expected(cases)
    @pytest.mark.parametrize(
        'string, pair, expected', [(*k, v) for k, v in cases.items()]
    )
    def test_iter(self, string, pair, expected):
        assert list(Parser(pair)._iter(string, must_close=-1)) == expected


    # @pytest.mark.parametrize('string', ['0{2{4,6,8}{}{3,5{{{9}}}}}'])
    # def test_iterate(self, string):
    #     for b, (i, j) in braces.iterate(string):
    #         assert b == string[i + 1 : j]

    @pytest.mark.parametrize('depth', range(7))
    def test_depth_filter(self, depth):
        itr = braces.iterate(
            '0{1{2{3{4{5{6{7}}}}}}}', condition=(level == depth)
        )
        pair = next(itr)
        assert pair.level == depth
        assert pair.enclosed[0] == str(depth + 1)


has_comma = op.has(',').within
test_unbracket = Expected(remove)(
    {
        mock.remove('', '()'): '',
        mock.remove('()', '()'): '',
        mock.remove('test()', '()'): 'test',
        mock.remove('test(())', '()'): 'test',
        mock.remove('test(()', '()'): 'test(()',
        mock.remove('{[(foo)]}', '()'): '{[foo]}',
        mock.remove('{{{hello world!}}}', '{}'): 'hello world!',
        mock.remove(
            '{some,thing}{}', '{}', Condition(enclosed=has_comma)
        ): 'some,thing{}',
        mock.remove(
            '{some,thing}{}', '{}', Condition(enclosed=negate(has_comma))
        ): '{some,thing}',
        mock.remove('{{1}}', '{}', level < 0): '{{1}}',
        mock.remove('{{1}}', '{}', level == 1): '{1}',
        mock.remove('{{hi{} {x}}}', '{}', level == 0): '{hi{} {x}}',
        mock.remove('{{hi{} {x}}}', '{}', is_outer): 'hi{} {x}',
        mock.remove('((hello) world)', '()', level == 0): '(hello) world',
        mock.remove('((hello) world)', '()', is_outer): '(hello) world',
        mock.remove(
            '{{Bai}, Yu and {Liu}, JiFeng}', '{}'
        ): 'Bai, Yu and Liu, JiFeng',
    }
)
# pytest.mark.skip(test_unbracket)

# test splitter
test_split = Expected(braces.split)(
    {
        '': [''],
        '...': ['...'],
        '{}': ['{}'],
        'x{}': ['x', '{}'],
        'x{}x': ['x', '{}', 'x'],
        '{}{}{}{}': ['{}', '{}', '{}', '{}'],
        'ch{1,2,{4..6}}...{,},xxx': [
            'ch',
            '{1,2,{4..6}}',
            '...',
            '{,}',
            ',xxx',
        ],
    },
    transform=list,
)

# Test csplit
test_csplit = Expected(csplit)(
    {
        '': [''],
        '...': ['...'],
        '{4..6}': ['{4..6}'],
        '{{4,6}}': ['{{4,6}}'],
        '{}{}{}{}': ['{}{}{}{}'],
        'a,b': ['a', 'b'],
        'ch{1,2,{4..6}}...{}': ['ch{1,2,{4..6}}...{}'],
        'a,b,c{d,e{f,g}}': ['a', 'b', 'c{d,e{f,g}}'],
        mock.csplit('!{!r::^11s}!', '{}', '!'): ['', '{!r::^11s}', ''],
        mock.csplit('::', '{}', ':', 1): '::'.split(':', 1),  # ['', ':']
        mock.csplit('::', '{}', ':'): '::'.split(':'),  # ['', '', '']
    },
    transform=list,
)

# ---------------------------------------------------------------------------- #
# Test `braces.depth` function
test_depth = Expected(braces.depth)(
    {
        '{}': 1,
        '': 0,
        '{{{{{}}}}}': 5,
        '{{{{{99dmckkcmmm/ {}}}}}}': 6,
        '{{{{{99dmckkcmmm/ {}{}}}}}{}}': 6,
    }
)


# def test_new_parser():
#     Parser()._index('[this(nested{set<of>[brackets]})]')
