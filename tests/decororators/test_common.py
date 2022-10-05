
from recipes.decorators import catch
import pytest


class TestCatch:

    @pytest.mark.parametrize(
        'action, kls, kws',
        [('warn', UserWarning, {}),
         ('raise', ValueError, {}),
         ('raise', TypeError, dict(alternate=TypeError))]
    )
    def test_decor(self, action, kls, kws):

        @catch(action=action, **kws)
        def foo():
            raise ValueError('Nope!')

        ctx = pytest.warns if issubclass(kls, Warning) else pytest.raises
        with ctx(kls):
            foo()

    
    @pytest.mark.parametrize(
        'action, kls, kws',
        [('warn', UserWarning, {}),
         ('raise', ValueError, {}),
         ('raise', TypeError, dict(alternate=TypeError))]
    )
    def test_context(self, action, kls, kws):
        ctx = pytest.warns if issubclass(kls, Warning) else pytest.raises
        with ctx(kls):
            with catch(action=action, **kws):
                raise ValueError('Nope!')
    
    @pytest.mark.parametrize('action', ('ignore', 'warn', 'raise'))
    def test_context_no_error(self, action):
        with catch(action=action):
            pass