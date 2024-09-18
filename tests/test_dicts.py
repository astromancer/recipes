
# std
import types
import pickle

# third-party
import pytest

# local
from recipes import dicts
from recipes.containers.dicts.core import VectorLookup
from recipes.containers.dicts import AttrDict, AttrReadItem, DictNode


# ---------------------------------------------------------------------------- #
@pytest.fixture()
def case_data_split():
    return dict(hello=0, world=1, foo=2)


def test_split_key(case_data_split):
    a, b = dicts.split(case_data_split, 'foo')
    assert a == dict(hello=0, world=1)
    assert b == {'foo': 2}


def test_split_multi_key(case_data_split):
    a, b = dicts.split(case_data_split, 'hello', 'world')
    assert a == {'foo': 2}
    assert b == dict(hello=0, world=1)


def test_split_tuple(case_data_split):
    a, b = dicts.split(case_data_split, ('hello', 'world'))
    assert a == {'foo': 2}
    assert b == dict(hello=0, world=1)


# ---------------------------------------------------------------------------- #
def test_dict_node():
    node = DictNode()
    node['x']['y']['z'] = 1


# ---------------------------------------------------------------------------- #
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

# ---------------------------------------------------------------------------- #


class TestLookup:

    class _TestLookup(VectorLookup, dict):
        pass

    test_case_vector_lookup = _TestLookup(a=1, b=2)

    def test_basic(self):
        case = self._TestLookup()
        # normal lookup
        case['hi'] = 0
        assert case['hi'] == 0
        case[0] = 0
        assert case[0] == 0

    @pytest.mark.parametrize('key', (..., None, slice(None), [0, 1]))
    def test_vector(self, key):

        case = self.test_case_vector_lookup
        assert case[key] == (1, 2)

        with pytest.raises(TypeError):
            case[key] = 1
