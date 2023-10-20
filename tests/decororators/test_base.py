# std
import pickle

# third-party
import pytest

# local
from recipes.decorators import decorator, Wrapper


# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #

# def wrap(fun):
#     return types.MethodType()

# class Case3:
#     @wrap
#     def method(self):
#         pass

# ---------------------------------------------------------------------------- #
# Decorating functions


@decorator
def case1():
    return 'case1'


@decorator()
def case2():
    return 'case2'


@pytest.mark.parametrize('i', [1, 2])
def test_func(i):
    fname = f'case{i}'
    assert eval(fname)() == fname


@pytest.mark.parametrize('i', [1, 2])
def test_pickle_func(i):
    fname = f'case{i}'
    func = eval(fname)
    stream = pickle.dumps(func)
    clone = pickle.loads(stream)
    assert clone() == fname
    # print(func.__factory__, clone.__factory__)

# ---------------------------------------------------------------------------- #
# Decorating methods


class Case0:
    @decorator
    def method1(self):
        return 'method1'

    @decorator()
    def method2(self):
        return 'method2'

    @decorator('hi', hello='world')
    def method3(self):
        return 'method3'


class Case1:
    def method(self):
        pass


def echo(_):
    return _


class Case2:
    @echo
    def method(self):
        pass


@pytest.mark.parametrize('i', [1, 2, 3])
def test_method(i):
    obj = Case0()
    name = f'method{i}'
    method = getattr(obj, name)
    assert method() == name


@pytest.mark.parametrize('obj', [
    Case1().method,
    Case2().method,
    #  Case3().method
])
def test_pickle(obj):
    clone = pickle.loads(pickle.dumps(obj))


@pytest.mark.parametrize('i', [1, 2, 3])
def test_pickle_method(i):
    obj = Case0()
    name = f'method{i}'
    s = pickle.dumps(getattr(obj, name))
    clone = pickle.loads(s)
    assert clone() == name

# ---------------------------------------------------------------------------- #
# Non-emmulation (for explicit wrapper objects, signature changing decorators)


def f():
    return ...


def test_wrapper():

    wrapped = decorator()(f, emulate=False)
    assert wrapped() is f()

    clone = pickle.loads(pickle.dumps(wrapped))
    assert clone() is f()
