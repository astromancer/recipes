
# std
import types

# third-party
import pytest, pickle

# local
from recipes.dicts import AVDict, AttrReadItem, AttrDict


def test_avdict():
    av = AVDict()
    av['x']['y'] = 'z'


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
