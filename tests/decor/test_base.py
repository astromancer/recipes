import pickle
import pytest
from recipes.decor.base import decorator  # , Wrapper

from pytest_cases import parametrize, fixture

# FUNC_TEMPLATE = """
# @decorator{argspec}
# def {name}():
#     return True
# """
# CLASS_TEMPLATE = """
# class {name}:
#     {pre}
#     @decorator{argspec}
#     {post}
#     def method(self):
#         return True
# """
# DEFAULTS = {'pre': '', 'post': ''}


# @fixture(scope='session',
#          params=['', '()', '(ignored)', '(0, kwo=0, **{"kw":0})'])
# def argspec(request):
#     return request.param


# def _make(template, **kws):
#     code = template.format(**{**DEFAULTS, **kws})
#     locals_ = {}
#     exec(code, None, locals_)
#     obj = locals_[kws['name']]
#     obj.__source__ = code
#     return obj


# def _generic_test(template, objname, argspec, **kws):
#     assert _make(template, name=objname, argspec=argspec, **kws)()


# class Testdecorator:

#     def test_func(self, argspec):
#         _generic_test(FUNC_TEMPLATE, 'func', argspec)

#     def test_class(self, argspec):
#         _generic_test(CLASS_TEMPLATE, 'Class', argspec)

#     @parametrize(pre=['@classmethod', ''],
#                  post = ['', '@classmethod'])
#     def test_classmethod(self, argspec, pre, post):
#         _generic_test(CLASS_TEMPLATE, 'Class', argspec, pre=pre, post=post)


# @count_calls
# def foo(a):
#     ...

# [*map(foo, '12345')]

class Case:
    @decorator
    def method1(self):
        return 'method1'

    @decorator()
    def method2(self):
        return 'method2'

    @decorator('hi', hello='world')
    def method3(self):
        return 'method3'


@decorator
def func1():
    return 'func1'


@decorator()
def func2():
    return 'func2'


@pytest.mark.parametrize('i', [1, 2, 3])
def test_method(i):
    obj = Case()
    name = f'method{i}'
    method = getattr(obj, name)
    assert method() == name


def deco(func):
    func.hi = 1


def work():
    return ...


class Case1:
    def method(self):
        pass


def echo(_):
    return _

# def wrap(fun):
#     return types.MethodType()


class Case2:
    @echo
    def method(self):
        pass

# class Case3:
#     @wrap
#     def method(self):
#         pass


@pytest.mark.parametrize('obj', [  # Wrapper(work, deco),
    Case1().method,
    Case2().method,
    #  Case3().method
])
def test_pickle(obj):
    clone = pickle.loads(pickle.dumps(obj))


@pytest.mark.parametrize('i', [1, 2, 3])
def test_pickle_method(i):
    obj = Case()
    name = f'method{i}'
    s = pickle.dumps(getattr(obj, name))
    clone = pickle.loads(s)
    assert clone() == name


@pytest.mark.parametrize('i', [1, 2])
def test_func(i):
    fname = f'func{i}'
    assert eval(fname)() == fname


@pytest.mark.parametrize('i', [1, 2])
def test_pickle_func(i):
    fname = f'func{i}'
    func = eval(fname)
    clone = pickle.loads(pickle.dumps(func))
    assert clone() == fname
