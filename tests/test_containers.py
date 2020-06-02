from collections import UserList

from recipes.containers import OfTypes

import pytest


def test_type_checking():
    class Container(UserList, OfTypes(int)):
        pass

    Container([1, 2, 3])

    with pytest.raises(TypeError):
        return Container([1., 2., 3.])

