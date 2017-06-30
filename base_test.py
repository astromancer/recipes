from decor.base import OptionalArgumentsDecorator

@OptionalArgumentsDecorator
def foo1():
    print('foo1')


@OptionalArgumentsDecorator()
def foo2():
    print('foo2')


class Foo():
    @OptionalArgumentsDecorator
    def method1(self):
        print('method1')

    @OptionalArgumentsDecorator()
    def method2(self):
        print('method2')


# try:
#     # foo1()
#     # foo2()
#
#     foo = Foo()
#     foo.method1()
#     # foo.method2()
# except:
from IPython import embed
embed()