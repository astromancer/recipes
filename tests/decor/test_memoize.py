# pylint: skip-file

from inspect import signature
from collections import Hashable, OrderedDict as odict
from recipes.memoize import (to_file, check_hashable_defaults, get_key, LRUCache,
                             PersistantCache)
import pickle
import tempfile
import pytest

# @memoize.to_file('~/work/.test_cache')
# def foo(n):
#     return n*2


# for i in range(10):
#     foo(i)
#     foo(i)

@pytest.fixture(params=[LRUCache(2),
                        PersistantCache(tempfile.mktemp(), 2)]
                )
def cache(request):
    return request.param


class TestLRUCache:
    def test_pickle(self, cache):
        clone = pickle.loads(pickle.dumps(cache))
        assert type(clone) is type(cache)
        assert clone == cache

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


# class TestPersistentRLUCache():
#     pass


# some template classes / functions for testing exceptions on non-hashable
# default arguments
class Foo():
    def foo(self, a, b=[1], *c, **kws):
        pass

    @classmethod
    def bar(cls, a, b=[1], *c,  **kws):
        pass


def bar(a, b=[1], *c, **kws):
    pass


class TestMomoizeDecorator():

    @pytest.mark.parametrize('func', [Foo().foo, Foo.bar, bar])
    def test_hashable_defaults(self, func):
        with pytest.raises(TypeError):
            check_hashable_defaults(func)

    def test_nonhashable_warns(self, tmpdir):

        @to_file(tmpdir / 'test_cache0.pkl')
        def foo(a=1):
            pass

        with pytest.warns(UserWarning):
            foo([1])

    def test_caching(self, tmpdir):

        @to_file(tmpdir / 'test_cache1.pkl')
        def foo(a, b=0, *c, **kws):
            return a * 7 + b

        foo(6)
        assert foo.cache == {(('a', 6), ('b', 0), ('c', ())): 42}

        with pytest.warns(UserWarning):
            foo([1], [0])
            # UserWarning: Refusing memoization due to unhashable argument
            # passed to function 'foo': 'a' = [1]

        # cache unchanged
        assert foo.cache == {(('a', 6), ('b', 0), ('c', ())): 42}

        foo(6, hello='world')
        # new cache item for keyword arguments
        assert foo.cache == {
            (('a', 6), ('b', 0), ('c', ())): 42,
            (('a', 6), ('b', 0), ('c', ()), ('hello', 'world')): 42
        }

    def test_new(self, tmpdir):
        class Foo:
            @to_file(tmpdir / 'test_cache2.pkl')
            def __new__(cls, *args):
                return super().__new__(cls)

            def __init__(self, *args):
                self.args = args

        foo = Foo(1)
        # print(Foo.__new__.cache)
        assert Foo.__new__.cache[(('cls', Foo), ('args', (1,)))] is foo
        assert Foo(1) is foo

    def test_class(self, tmpdir):
        @to_file(tmpdir / 'test_cache3.pkl')
        class Moo:
            def __init__(self, *args):
                self.args = args

        moo = Moo(1)
        # print(Foo.__new__.cache)
        
        assert Moo.__new__.cache[(('cls', Moo), ('args', (1,)))] is moo
        assert Moo(1) is moo 
        