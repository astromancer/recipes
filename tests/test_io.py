
from recipes.io.utils import iter_lines
import pytest
from pathlib import Path
from recipes.io import bash


from recipes.testing import Expect, mock, expected

# @pytest.fixture(scope="session")
# def tempfiles(tmp_path_factory):
#     """Generate a bunch of empty files for testing"""
#     folder = tmp_path_factory.mktemp('testfiles')
#     filenames = []
#     for i in range(7, 22):
#         path = folder / f'file{i:>04}.test'
#         path.touch()
#         filenames.append(path)
#     return filenames


@pytest.fixture(scope="session")
def filename(tmp_path_factory):
    """Generate a bunch of empty files for testing"""
    filename = tmp_path_factory.getbasetemp() / 'testfile.txt'
    with filename.open('w') as fp:
        for i in range(10):
            fp.write(f'{i}\n')
    return filename


patterns = {
    'test*{7,8}.test':  ['test*7.test', 'test*8.test'],

    '*00{10..21}.*':    ['*0010.*', '*0011.*',
                         '*0012.*', '*0013.*',
                         '*0014.*', '*0015.*',
                         '*0016.*', '*0017.*',
                         '*0018.*', '*0019.*',
                         '*0020.*', '*0021.*'],

    '/home/work/recipes/recipes/{__init__,dicts,interactive,iter}.py':
        ['/home/work/recipes/recipes/__init__.py',
         '/home/work/recipes/recipes/dicts.py',
         '/home/work/recipes/recipes/interactive.py',
         '/home/work/recipes/recipes/iter.py'],

    '/home/work/recipes/recipes/{logg,str,test}ing.py':
        ['/home/work/recipes/recipes/logging.py',
         '/home/work/recipes/recipes/string.py',
         '/home/work/recipes/recipes/testing.py']

}

inverted_patterns = list(zip(patterns.values(), patterns.keys()))

# tests
# ---------------------------------------------------------------------------- #
test_brace_expand = Expect(bash.brace_expand)(patterns)

test_brace_contract = Expect(bash.brace_contract)(
    inverted_patterns +
    [(range(10), '{0..9}')]
)
# pytest.mark.skip(test_brace_expand, test_brace_contract)


# ('test*[78].fits',
#     ['testfile0007.fits', 'testfile0008.fits',
#      'testfile0017.fits', 'testfile0018.fits']),

# # globbing pattern
# ('test*0[7..8].fits',
#     ['testfile0007.fits', 'testfile0008.fits']),


def srange(*section):
    return list(map(str, range(*section)))


def brange(*section):
    return list(map(str.encode, srange(*section)))

def bnrange(*section):
    return [b + b'\n' for b in brange(*section)]

test_iter_lines = Expect(iter_lines)(
    {mock.iter_lines(filename, 5):                      srange(5),
     mock.iter_lines(filename, 5, 10):                  srange(5, 10),
     mock.iter_lines(filename, 3, mode='rb'):           brange(3),
     mock.iter_lines(filename, 3, mode='rb', strip=''): bnrange(3)},
    transform=list
)

# @pytest.mark.parametrize(
#     'section, mode, strip, result',
#     [((5, ),  'r', None,  srange(5)),
#      ((3, 8), 'r', None,  srange(3, 8)),
#       ((3,),  'rb', None, brange(3)),
#       ((3,),  'rb', '',   bnrange(3)) ]
#
# )
# def test_iter_lines(filename, section, mode, strip, result):
#     print(filename)
#     assert list(iter_lines(filename, *section, mode=mode, strip=strip)) == result
