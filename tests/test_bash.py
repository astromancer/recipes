
from recipes.string.brackets import braces

import pytest

from recipes import bash
import textwrap as txw


from recipes.testing import Expect, mock, expected, Throws
# from recipes.dicts import invert


filenames = ('20130616.0030',
             '20130616.0031',
             '20130617.0030',
             '20130617.0031',
             '20130618.0030',
             '20130618.0031',
             '202130615.0030',
             '202130615.0031',
             '202130615.0032',
             'SHA_20150606.0300',
             'SHA_20150715.0200',
             'SHA_20150904.0201',
             'SHA_20150904.0202',
             'SHA_20150905.0101',
             'SHA_20160706.0007',
             'SHA_20160707.0030',
             'SHA_20160707.0031',
             'SHA_20160711.0001',
             'SHA_20171002.0010',
             'SHA_20171002.0011',
             'SHA_20200721.0030')

expand_once_patterns = {
    'test7.test': ['test7.test'],
    'test{7}.test': ['test7.test'],
    'test*{7,8}.test':  ['test*7.test', 'test*8.test'],

    '*00{10..21}.*':    ['*0010.*', '*0011.*',
                         '*0012.*', '*0013.*',
                         '*0014.*', '*0015.*',
                         '*0016.*', '*0017.*',
                         '*0018.*', '*0019.*',
                         '*0020.*', '*0021.*'],

    '/root/{__init__,dicts,interactive,iter}.py':
        ['/root/__init__.py',
         '/root/dicts.py',
         '/root/interactive.py',
         '/root/iter.py'],

    '/root/{logg,str,test}ing.py':
        ['/root/logging.py',
         '/root/string.py',
         '/root/testing.py'],
}
expand_multi_patterns = {
    '2013061{6..8}.003{0,1}':
        ['20130616.0030',
         '20130617.0030',
         '20130618.0030',
         '20130616.0031',
         '20130617.0031',
         '20130618.0031'],

    'root/{ch{1,2,{4..6}},main{1,2},{1,2}test}/*.png':
        ['root/ch1/*.png',
         'root/ch2/*.png',
         'root/ch4/*.png',
         'root/ch5/*.png',
         'root/ch6/*.png',
         'root/main1/*.png',
         'root/main2/*.png',
         'root/1test/*.png',
         'root/2test/*.png']}
all_expand_patterns = {**expand_once_patterns, **expand_multi_patterns}

# ---------------------------------------------------------------------------- #
# helper


def invert(dict_):
    return zip(dict_.values(), dict_.keys())


# tests
# ---------------------------------------------------------------------------- #
# test splitter
test_splitter = Expect(bash.xsplit)(
    {'{4..6}':           ['{4..6}'],
     '{4,6}':            ['{4,6}'],
     '4,6':              ['4', '6'],
     'ch{1,2,{4..6}}':   ['ch{1,2,{4..6}}']},
    transform=list)

# ---------------------------------------------------------------------------- #
# brace expand
test_brace_expand = Expect(bash.brace_expand)(
    all_expand_patterns, transform=sorted
)

# ---------------------------------------------------------------------------- #
# test single contraction
expand_once_patterns.pop('test{7}.test')
test_single_contraction = Expect(bash.contract)(
    [*invert(expand_once_patterns),
     (range(10),                        '{0..9}'),
     (['*001{0..9}.*', '*002{0,1}.*'],  '*00{1{0..9},2{0,1}}.*'),
     ([],                               Throws(ValueError))]
)

# ---------------------------------------------------------------------------- #
# test_full_contraction


def components(s):
    return sorted(braces.match(s, False).split(','))


test_full_contraction = Expect(bash.brace_contract)(
    (*invert(expand_multi_patterns),
     ([], Throws(ValueError))),
    transform=components
)
# def test_full_contraction(bash.brace_contract):
#     result = bash.brace_contract(items)
#     assert components(result) == components(expected)


test_contract_expand = Expect(bash.brace_contract)(
    [([items], items) for items in (*all_expand_patterns.values(), filenames)],
    transform=sorted
)

# @pytest.mark.parametrize('items', [*all_expand_patterns.values(), filenames])
# def test_contract_expand(items):
#     regen = bash.brace_expand(bash.brace_contract(items))
#     assert sorted(regen) == sorted(items)

# ---------------------------------------------------------------------------- #
# test rendering trees


def make_id(name, n):
    for i in range(n):
        yield f'{name}{i}'


def make_ids(names, n=10):
    for names in zip(*(make_id(name, n) for name in names)):
        yield '-'.join(names)


@expected(
    {(filenames, 0):
        """
        ├20
        │ ├13061
        │ │    ├6.003
        │ │    │    ├0
        │ │    │    └1
        │ │    ├7.003
        │ │    │    ├0
        │ │    │    └1
        │ │    └8.003
        │ │         ├0
        │ │         └1
        │ └2130615.003
        │            ├0
        │            ├1
        │            └2
        └SHA_20
              ├1
              │├50
              ││ ├606.0300
              ││ ├715.0200
              ││ └90
              ││   ├4.020
              ││   │    ├1
              ││   │    └2
              ││   └5.0101
              │├607
              ││  ├0
              ││  │├6.0007
              ││  │└7.003
              ││  │     ├0
              ││  │     └1
              ││  └11.0001
              │└71002.001
              │         ├0
              │         └1
              └200721.0030
        """,
     (filenames, 1):
        """
        ├20
        │ ├13061
        │ │    ├6.003{0,1}
        │ │    ├7.003{0,1}
        │ │    └8.003{0,1}
        │ └2130615.003{0..2}
        └SHA_20
              ├1
              │├50
              ││ ├{606.03,715.02}00
              ││ └90
              ││   ├4.020{1,2}
              ││   └5.0101
              │├607
              ││  ├0
              ││  │├6.0007
              ││  │└7.003{0,1}
              ││  └11.0001
              │└71002.001{0,1}
              └200721.0030
        """
     },
    ids=make_ids(['strings', 'depth'])
)
def test_tree(strings, depth, expected):
    root = bash.get_tree(strings, depth)
    assert root.render() == txw.dedent(expected)

# pytest.mark.skip(test_brace_expand, test_brace_contract)


# ('test*[78].fits',
#     ['testfile0007.fits', 'testfile0008.fits',
#      'testfile0017.fits', 'testfile0018.fits']),

# # globbing pattern
# ('test*0[7..8].fits',
#     ['testfile0007.fits', 'testfile0008.fits']),
