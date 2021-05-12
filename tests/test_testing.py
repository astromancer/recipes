from recipes.testing import Expect, Throws, mock
import pytest

# pylint: disable=unused-argument
# pylint: disable=missing-function-docstring


def fun0():
    return


def fun1(a, b=2, *args, c=3, **kws):
    return a, b, c, args, kws


def fun2(a, /):
    return 1


def throws1():
    raise ValueError()


class SomeClass:
    def meth0(self, a, b=2, *args, c=3, **kws):
        return a, b, c, args, kws

    @classmethod
    def meth1(cls, a, b=2, *args, c=3, **kws):
        print(f'\nmeth1: {a=} {b=}, {c=}, {args=}, {kws=}')
        return a, b, c, args, kws


# test_fun0 = Expect(fun0)({(): None})




for f in (fun1, ):#SomeClass().meth0, SomeClass.meth1):
    test = Expect(f)({
        mock(1):            (1, 2, 3, (), {}),
        mock(1, 1):         (1, 1, 3, (), {}),
        mock(1, b=1):       (1, 1, 3, (), {}),
        mock(1, 1, 1):      (1, 1, 3, (1,), {}),
        mock(1, 1, 1, 1):   (1, 1, 3, (1, 1), {}),
        mock(1, 1, c=1):    (1, 1, 1, (), {}),
        mock(1, x=1):       (1, 2, 3, (), {'x':1}),
    })
    exec(f'test_{f.__name__} = test')

test_throws = Expect(throws1)({(): Throws(ValueError)})



# test_fun1 = Expect(fun1)({
#     mock(1):            RETURNS,
#     mock(1, 1):         RETURNS,
#     mock(1, b=1):       RETURNS,
#     mock(1, 1, 1):      RETURNS,
#     mock(1, 1, c=1):    RETURNS,
#     mock(1, x=1):       RETURNS,
# })


# test_meth0 = Expect(SomeClass().meth0)({
#     mock(1):            RETURNS,
#     mock(1, 1):         RETURNS,
#     mock(1, b=1):       RETURNS,
#     mock(1, 1, 1):      RETURNS,
#     mock(1, 1, c=1):    RETURNS,
#     mock(1, x=1):       RETURNS,
# })


# test_meth1 = Expect(SomeClass.meth1)({
#     mock(1):            RETURNS,
#     mock(1, 1):         RETURNS,
#     mock(1, b=1):       RETURNS,
#     mock(1, 1, 1):      RETURNS,
#     mock(1, 1, c=1):    RETURNS,
#     mock(1, x=1):       RETURNS,
# })

