from collections import UserList

from recipes.containers import OfTypes

import pytest

import numpy as np


def test_type_checking():
    class Container(UserList, OfTypes(int)):
        pass

    Container([1, 2, 3])

    with pytest.raises(TypeError):
        return Container([1., 2., 3.])

    class Container(UserList, OfTypes(numbers.Real)):
        pass

    Container([1, 2., 3, np.array(1.)])
