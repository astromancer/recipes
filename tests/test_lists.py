# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring


from recipes.lists import split
from recipes.testing import Expect


# def lists(iters):
#     if isinstance(iters, list):
#         return iters
#     return list(map(list, iters))


test_split = Expect(split)([
    (([1, 2, 3], []),            [[1, 2, 3]]),
    (([1, 2, 3], 1),             [[1], [2, 3]]),
    (([1, 2, 3], [1, 2]),        [[1], [2], [3]]),
    (([1, 2, 3], [0, 2]),        [[], [1, 2], [3]])
])
