from recipes.decor.base import Decorator


class Foo():
    @Decorator
    def method1(self):
        print('method1')

    @Decorator()
    def method2(self):
        print('method2')

    @Decorator('hi', hello='world')
    def method3(self):
        print('method3')


@Decorator
def foo1():
    print('foo1')


@Decorator()
def foo2():
    print('foo2')


def test_decorator():
    # test
    foo = Foo()
    foo.method1()
    foo.method2()
    foo.method3()

    foo1()
    foo2()
