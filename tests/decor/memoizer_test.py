from collections import Hashable, OrderedDict as odict
from recipes.decor.memoize import to_file, check_hashable_defaults, LRUCache
import pickle
import pytest

# @memoize.to_file('~/work/.test_cache')
# def foo(n):
#     return n*2


# for i in range(10):
#     foo(i)
#     foo(i)


def test_lru_cache():
    cache = LRUCache(2)

    clone = pickle.loads(pickle.dumps(cache))
    assert clone.capacity == 2
    

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


class Foo():
    def foo(self, a, b=[1],  *c, **kws):
        pass

    @classmethod
    def bar(cls, a, b=[1], *c,  **kws):
        pass


def bar(a, b=[1], *c, **kws):
    pass


@pytest.mark.parametrize("func", [Foo().foo, Foo.bar, bar])
def test_hashable_defaults(func):
    with pytest.raises(TypeError):
        check_hashable_defaults(func)


def test_nonhashable_warns(tmpdir):
    @to_file(tmpdir/'test_cache0.pkl')
    def foo(a=1):
        pass

    with pytest.warns(UserWarning):
        foo([1])


def test_caching(tmpdir):
    @to_file('/tmp/test_cache5.pkl')
    def foo(a, b=0, *c, **kws):
        '''this my compute heavy function'''
        return a * 7 + b
        
    foo(6)
    print(foo.cache) # LRUCache([((('a', 6), ('b', 0), ('c', ())), 42)])
    foo([1], [0])    # UserWarning: Refusing memoization due to
                        # unhashable argument passed to function 
                        # 'foo': 'a' = [1]
    print(foo.cache) # LRUCache([((('a', 6), ('b', 0), ('c', ())), 42)])
                        # cache unchanged
    foo(6, hello='world')
    print(foo.cache)  
    # new cache item for keyword arguments
    # LRUCache([((('a', 6), ('b', 0), ('c', ())), 42),
                ((('a', 6), ('b', 0), ('c', ()), ('hello', 'world')), 42)])