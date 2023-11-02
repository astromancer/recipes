
# std
import types
import pickle

# third-party
import pytest

# local
from recipes import dicts
from recipes.dicts import AttrDict, AttrReadItem, DictNode


def test_split1():
    case = dict(hello=0, world=1, foo=2)
    a, b = dicts.split(case, 'foo')
    assert a == dict(hello=0, world=1)
    assert b == {'foo': 2}


def test_split2():
    case = dict(hello=0, world=1, foo=2)
    a, b = dicts.split(case, 'hello', 'world')
    assert b == dict(hello=0, world=1)
    assert a == {'foo': 2}

def test_split3():
    case = dict(hello=0, world=1, foo=2)
    a, b = dicts.split(case, ('hello', 'world'))
    assert b == dict(hello=0, world=1)
    assert a == {'foo': 2}


def test_dict_node():
    node = DictNode()
    node['x']['y']['z'] = 1


class TestAttrDict:
    def test_basic(self):
        x = AttrReadItem(hello=0, world=2)
        assert (x.hello, x.world) == (0, 2)

        x['keys'] = None
        assert isinstance(x.keys, types.BuiltinFunctionType)
        assert x['keys'] is None

    @pytest.mark.parametrize('kls', (AttrReadItem, AttrDict))
    def test_copy(self, kls):
        x = kls(hello=0, world=2)
        assert isinstance(x.copy(), kls)

    def test_pickle(self):
        z = AttrDict(hello=0, world=2)
        z2 = pickle.loads(pickle.dumps(z))

        z2['hi'] = 1
        assert z2.hi == 1

        z2.bye = -1
        assert z2['bye'] == -1
