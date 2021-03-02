from recipes import op
import pytest
# from recipes.testing import Expect

x = dict(hello = 'world')

# @pytest.mark.parametrize(
#     ''
# )
def test_getitem():
    assert op.getitem('hello')(x) == 'world'
    assert op.getitem('foo', default=None)(x) is None
    with pytest.raises(KeyError):
        op.getitem('foo')(x)

