
import pytest

from pathlib import Path

from recipes import io
from recipes.testing import Expected, mock

# ---------------------------------------------------------------------------- #
# Helper functions


def srange(*section):
    return list(map(str, range(*section)))


def brange(*section):
    return list(map(str.encode, srange(*section)))


def bnrange(*section):
    return [b + b'\n' for b in brange(*section)]


# ---------------------------------------------------------------------------- #
# Fixtures


@pytest.fixture(scope="session")
def filename(tmp_path_factory):
    """Generate a bunch of empty files for testing"""
    filename = tmp_path_factory.getbasetemp() / 'testfile.txt'
    with filename.open('w') as fp:
        for i in range(10):
            fp.write(f'{i}\n')
    return filename



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

# def pytest_generate_tests(metafunc):
#     if "fixture1" in metafunc.fixturenames:
#         metafunc.parametrize("fixture1", ["one", "uno"])
#     if "fixture2" in metafunc.fixturenames:
#         metafunc.parametrize("fixture2", ["two", "duo"])

# def test_foobar(fixture1, fixture2):
#     assert type(fixture1) == type(fixture2)


test_iter_lines = Expected(io.iter_lines)(
    {mock.iter_lines(filename, 5):                      srange(5),
     mock.iter_lines(filename, 5, 10):                  srange(5, 10),
     mock.iter_lines(filename, 3, mode='rb'):           brange(3),
     mock.iter_lines(filename, 3, mode='rb', strip=''): bnrange(3)},
    transform=list
)


# test_iter_files = Expected(io.iter_files)(
#     ()
# )

# TODO: test iter_files!!!!!!!
# iter_files('/root/{main,ch*}', 'tex') # with expansion
# iter_files('/root/', 'tex', True) #  recursive walk
#
# 
# l = set(map(str, iter_files('/home/hannes/Desktop/PhD/thesis/build/', 'tex', True)))
# g = set(glob.glob('/home/hannes/Desktop/PhD/thesis/build/**/*.tex',
# recursive=True))
# g.symmetric_difference(l)
