import pytest

from recipes.lists import split, lists
from recipes.testing import Expect


test_split = Expect(split)({
    ((1, 2, 3), 1):             ([1], [2, 3]),
    ((1, 2, 3), (1, 2)):        ([1], [2], [3]),
    ((1, 2, 3), (0, 2)):        ([], [1, 2], [3])
},
    transform=lists)
