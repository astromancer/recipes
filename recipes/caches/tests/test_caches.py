# pylint: skip-file
import logging
from inspect import signature
from collections import OrderedDict as odict
from recipes.caches import to_file, Cache, CacheEncoder, CacheDecoder
from recipes.caches.memoize import check_hashable_defaults
from pathlib import Path
import pickle
import tempfile
import pytest
import itertools as itt
import json
from collections import defaultdict

# setup logging
logging.basicConfig()
rootlog = logging.getLogger()
rootlog.setLevel(logging.DEBUG)


# import pickle
# from collections import OrderedDict as odict
# from recipes.caches import LRUCache

# class _Test(LRUCache, odict):
#     def __reduce__(self):
#         print('HERE!')
#         red = super().__reduce__()
#         print(red)
#         return red

# od = _Test(2)
# od[1] = 1
# pickle.loads(pickle.dumps(od))


# @caches.to_file('~/work/.test_cache')
# def foo(n):
#     return n*2


# for i in range(10):
#     foo(i)
#     foo(i)

counters = defaultdict(itt.count)
tmpdir = Path(tempfile.mkdtemp())


def get_tmp_filename(ext='pkl'):
    return tmpdir / f'test_cache{next(counters[ext])}.{ext}'

# --------------------------------- Fixtures --------------------------------- #


@pytest.fixture(params=[Cache(2),
                        Cache(2, get_tmp_filename('json')),
                        Cache(2, get_tmp_filename('pkl'))])
def cache(request):
    return request.param

# -------------------------------- Test Cases -------------------------------- #

# some template classes / functions for testing exceptions on non-hashable
# default arguments


class _TestCaseNonHash():
    def foo(self, a, b=[1], *c, **kws):
        pass

    @classmethod
    def bar(cls, a, b=[1], *c,  **kws):
        pass


def _test_func_non_hash(a, b=[1], *c, **kws):
    pass


@to_file(get_tmp_filename())
def _test_func0(a=1):
    pass


@to_file(get_tmp_filename())
def _test_func1(a, b=0, *c, **kws):
    return a * 7 + b

# these test classes have to be globally scoped in order to be picklable


class _TestCase0:
    @to_file(get_tmp_filename())
    def __new__(cls, *args):
        return super().__new__(cls)

    def __init__(self, *args):
        self.args = args



class _TestCase1:
    def __init__(self, *args):
        self.args = args


# ----------------------------------- Tests ---------------------------------- #
def test_serialize(cache):
    cache[1] = 1   # this will save the cache
    if cache.filename is None:
        return

    clone = Cache.load(cache.filename)
    assert type(clone) is type(cache)
    assert clone == cache
    assert clone.capacity == cache.capacity
    assert clone.filename == cache.filename


class TestLRUCache:
    def test_queue(self, cache):
        cache[1] = 1
        assert cache == odict([(1, 1)])
        cache[2] = 2
        assert cache == odict([(1, 1), (2, 2)])
        cache[1]
        assert cache == odict([(2, 2), (1, 1)])
        cache[3] = 3
        assert cache == odict([(1, 1), (3, 3)])
        cache.get(2)
        assert cache == odict([(1, 1), (3, 3)])
        cache[4] = 4
        assert cache == odict([(3, 3), (4, 4)])
        cache.get(1)
        assert cache == odict([(3, 3), (4, 4)])
        cache.get(3)
        assert cache == odict([(4, 4), (3, 3)])
        cache[4]
        assert cache == odict([(3, 3), (4, 4)])


class TestPersistentCache():
    # def test_load(tmpdir):

    def test_save(self):
        filename = get_tmp_filename()
        cache = Cache(2, filename)
        cache[1] = 1

        clone = Cache(2, filename)
        assert clone[1] == 1


class TestMomoizeDecorator():

    @pytest.mark.parametrize('func',
                             [_TestCaseNonHash().foo,
                              _TestCaseNonHash.bar,
                              _test_func_non_hash])
    def test_hashable_defaults(self, func):
        with pytest.raises(TypeError):
            check_hashable_defaults(func)

    def test_nonhashable_warns(self):
        with pytest.warns(UserWarning):
            _test_func0([1])

    def test_no_call(self):
        class Foo:
            called = False

            @to_file(None)
            def __call__(self, a):
                self.called = True

        foo = Foo()
        foo(1)
        foo.called = False
        foo(1)
        assert foo.called is False

    def test_caching(self):

        _test_func1(6)
        assert _test_func1.cache == {(('a', 6), ('b', 0), ('c', ())): 42}

        with pytest.warns(UserWarning):
            _test_func1([1], [0])
            # UserWarning: Refusing memoization due to unhashable argument
            # passed to function '_test_func1': 'a' = [1]

        # cache unchanged
        assert _test_func1.cache == {(('a', 6), ('b', 0), ('c', ())): 42}

        _test_func1(6, hello='world')
        # new cache item for keyword arguments
        assert _test_func1.cache == {
            (('a', 6), ('b', 0), ('c', ())): 42,
            (('a', 6), ('b', 0), ('c', ()), ('hello', 'world')): 42
        }

    def test_new(self):

        obj = _TestCase0(1)
        # print(Foo.__new__.cache)
        assert (_TestCase0.__new__.cache[(('cls', _TestCase0), ('args', (1,)))]
                is obj)
        assert _TestCase0(1) is obj

    @pytest.mark.parametrize('ext', ['pkl', 'json'])
    def test_class(self, ext):
        decor = to_file(get_tmp_filename(ext))
        kls = decor(_TestCase1)
        obj = kls(1)
        # print(Foo.__new__.cache)

        assert (kls.__new__.cache[(('cls', kls), ('args', (1,)))]
                is obj)
        assert kls(1) is obj
