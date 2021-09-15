# pylint: skip-file


# std
from recipes.caches.decor import CacheRejectionWarning
import logging
import tempfile
import itertools as itt
from pathlib import Path
from collections import OrderedDict as odict, defaultdict

# third-party
import pytest
import numpy as np

# local libs
from recipes.caches import Cache
from recipes.caches.decor import (check_hashable_defaults, Ignore, Reject,
                                  cached, to_file)


# setup logging
logging.basicConfig()
rootlog = logging.getLogger()
rootlog.setLevel(logging.DEBUG)

# TODO: Test inheritance with decorated methods!


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
# default arguments. These test classes have to be globally scoped so we can
# pickle them


class Case0:
    # test decorating the constructor methods
    @to_file(get_tmp_filename())
    def __new__(cls, *args):
        return super().__new__(cls)

    def __init__(self, *args):
        self.args = args


# @to_file(get_tmp_filename())  # FIXME
# class Case1:
#     def __init__(self, *args):
#         self.args = args


class Case2:
    def __call__(self, a):
        pass


class _CheckIfCalled:
    # helper that simply sets the `called` attribute to True when called
    called = False

    @cached
    def __call__(self, a, b=None):
        self.called = True


class CaseNonHashableDefaults:
    def foo(self, a, b=[1], *c, **kws):
        pass

    @classmethod
    def bar(cls, a, b=[1], *c,  **kws):
        pass


def case_func_non_hash(a, b=[1], *c, **kws):
    pass


@to_file(get_tmp_filename())
def case0(a=1):
    pass


@to_file(get_tmp_filename())
def case1(a, b=0, *c, **kws):
    return a * 7 + b


@cached
def case1b(a, b=0, *c, **kws):
    return a * 7 + b


@cached(ignore='verbose')
def case2(a, verbose=True):
    return


@cached(typed={'verbose': Ignore()})
def case3(a, verbose=True):
    return


@cached(typed={'verbose': Ignore(silent=False)})
def case4(a, verbose=True):
    return


@cached(typed={'a': int})
def case5(a):
    return


@cached(typed={'file': lambda _: _ or Reject(silent=False)})
def case6(file, **kws):
    if file:
        return 1



# ----------------------------------- Tests ---------------------------------- #


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


class TestPersistence():

    filename = get_tmp_filename()
    
    def test_serialize(self, cache):
        cache[1] = 1   # this will save the cache
        if cache.filename is None:
            return

        clone = Cache.load(cache.filename)
        assert type(clone) is type(cache)
        assert clone == cache
        assert clone.capacity == cache.capacity
        assert clone.filename == cache.filename

    def test_save(self):
        filename = self.filename
        cache = Cache(2, filename)
        cache[1] = 1

        clone = Cache(2, filename)
        assert clone[1] == 1
        
    def test_load(self):
        filename = self.filename
        cache = Cache(2, filename)
        1 in cache
        

class TestDecorator():

    @pytest.mark.parametrize(
        'func',
        [CaseNonHashableDefaults().foo,
         CaseNonHashableDefaults.bar,
         case_func_non_hash])
    def test_hashable_defaults(self, func):
        with pytest.raises(TypeError):
            check_hashable_defaults(func)

    def test_nonhashable_warns(self):
        with pytest.warns(CacheRejectionWarning):
            case0([1])

    def test_warn_no_params(self):
        with pytest.warns(UserWarning):
            @cached
            def case7():
                pass
    
    def test_warn_not_callable(self):
        with pytest.warns(UserWarning):
            cached()(Case0())
            
    
    def test_no_call(self):
        chk = _CheckIfCalled()
        chk(1)
        chk.called = False
        chk(1)
        assert not chk.called

    @pytest.mark.parametrize('func', [case1])
    def test_caching_basic(self, func):

        func(6)
        initial = (6, 0, (), ())
        assert func.__cache__ == {initial: 42}

        with pytest.warns(CacheRejectionWarning):
            func([1], [0])
            # UserWarning: Refusing memoization due to unhashable argument
            # passed to function 'func': 'a' = [1]

        # cache unchanged
        assert func.__cache__ == {initial: 42}

        func(6, hello='world')
        # new cache item for keyword arguments
        assert func.__cache__ == {
            initial: 42,
            (6, 0, (), (('hello', 'world'),)): 42
        }

    def test_auto_init(self):
        self.test_caching_basic(case1b)

    def test_caching_kws(self):
        chk = _CheckIfCalled()
        chk(a=1, b=2)
        chk.called = False
        chk(b=2, a=1)
        assert not chk.called

    def test_new(self):

        obj = Case0(1)
        # print(Foo.__new__.cache)

        assert Case0.__new__.__cache__[(Case0, (1,))] is obj
        assert Case0(1) is obj

    # @pytest.mark.parametrize('ext', ['pkl'])
    def test_class(self):  # , ext):
        # decor = to_file(get_tmp_filename(ext))
        # kls = decor(Case1)

        obj = Case2()
        cached()(obj)

        # obj = Case1(1)
        # print(Foo.__new__.cache)

        # assert kls.__new__.cache[(kls, (1,))] is obj
        # Case1.__cache__[((1, ),)] is obj
        # assert Case1(1) is obj

    @pytest.mark.parametrize('func', [case2, case3])
    def test_ignore(self, func):

        func(1, verbose=True)
        initial = dict(func.__cache__)

        func(1, verbose=False)
        assert func.__cache__ == initial
        func(1, True)
        assert func.__cache__ == initial

    # def test_ignore_warns(self):
    #     with pytest.warns(UserWarning):
    #         self.test_ignore(case4)

    def test_rejection(self):
        func = case6
        func(1)
        initial = dict(func.__cache__)

        with pytest.warns(CacheRejectionWarning):
            func(None)

        assert func.__cache__ == initial

    def test_typed(self):
        func = case5
        func(1)
        initial = dict(func.__cache__)

        for a in (1., '1', np.array(1)):
            func(a)
            assert func.__cache__ == initial

    def test_typed_raises_on_invalid_name(self):
        with pytest.raises(ValueError):
            @cached(typed={'a': int})
            def case6(b):
                return
