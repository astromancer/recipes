
from recipes.io.utils import iter_lines
import pytest
from pathlib import Path
from recipes.io import bash


from recipes.testing import Expect, expected

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
def file_with_content(tmp_path_factory):
    """Generate a bunch of empty files for testing"""
    folder = tmp_path_factory.getbasetemp()
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


test_brace_expand = Expect(bash.brace_expand)(patterns)

# @expected(patterns)
# def test_brace_expand(pattern, result):
#     assert bash.brace_expand(pattern) == result


@pytest.mark.parametrize(
    'pattern, result',
    [(range(10), '{0..9}')]
    + list(zip(patterns.values(), patterns.keys()))
)
def test_brace_contraction(pattern, result):
    assert bash.brace_contract(pattern) == result

# ('test*[78].fits',
#     ['testfile0007.fits', 'testfile0008.fits',
#      'testfile0017.fits', 'testfile0018.fits']),

# # globbing pattern
# ('test*0[7..8].fits',
#     ['testfile0007.fits', 'testfile0008.fits']),


def srange(n):
    return list(map(str, range(5)))


def test_iter_lines(file_with_content):
    assert list(iter_lines(file_with_content, 5)) == srange(5)
