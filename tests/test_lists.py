# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring


from recipes.lists import split, split_like
from recipes.testing import Expected


# def lists(iters):
#     if isinstance(iters, list):
#         return iters
#     return list(map(list, iters))


test_split = Expected(split)([
    (([1, 2, 3], []),            [[1, 2, 3]]),
    (([1, 2, 3], 1),             [[1], [2, 3]]),
    (([1, 2, 3], [1, 2]),        [[1], [2], [3]]),
    (([1, 2, 3], [0, 2]),        [[], [1, 2], [3]])
])

test_split = Expected(split_like)([
    (([1, 2, 3], [[0], [0], [0]]), [[1], [2], [3]]),
])
