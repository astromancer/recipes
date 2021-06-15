from recipes.decor.base import Decorator

from pytest_cases import parametrize, fixture

FUNC_TEMPLATE = """
@Decorator{argspec}
def {name}():
    return True
"""
CLASS_TEMPLATE = """
class {name}:
    {pre}
    @Decorator{argspec}
    {post}
    def method(self):
        return True
"""
DEFAULTS = {'pre': '', 'post': ''}


# @fixture(scope='session',
#          params=['', '()', '(ignored)', '(0, kwo=0, **{"kw":0})'])
# def argspec(request):
#     return request.param


# def _make(template, **kws):
#     code = template.format(**{**DEFAULTS, **kws})
#     locals_ = {}
#     exec(code, None, locals_)
#     obj = locals_[kws['name']]
#     obj.__source__ = code
#     return obj


# def _generic_test(template, objname, argspec, **kws):
#     assert _make(template, name=objname, argspec=argspec, **kws)()


# class TestDecorator:

#     def test_func(self, argspec):
#         _generic_test(FUNC_TEMPLATE, 'func', argspec)

#     def test_class(self, argspec):
#         _generic_test(CLASS_TEMPLATE, 'Class', argspec)

#     @parametrize(pre=['@classmethod', ''],
#                  post = ['', '@classmethod'])
#     def test_classmethod(self, argspec, pre, post):
#         _generic_test(CLASS_TEMPLATE, 'Class', argspec, pre=pre, post=post)
        
        

        

@count_calls
def foo(a):
    ...
    
# [*map(foo, '12345')]

class Foo:
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
