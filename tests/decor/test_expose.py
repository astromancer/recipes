# from recipes.decor.tests import test_cases as tcx
# pylint: disable-all


def test_expose_decor():
    @expose.show
    def foo(a, b=1, *args, c=2, **kws):
        pass

    foo(88, 12, 11, c=4, y=1)



def test_expose_decor():
    @expose.args
    def foo(a, b=1, *args, c=2, **kws):
        pass

    foo(88, 12, 11, c=4, y=1)


#     # print(i)
#     # print(sig)
#     # print(ba)
#     ba.apply_defaults()
#     # print(ba)
#     print(f'{ba!s}'.replace('<BoundArguments ', fun.__qualname__).rstrip('>'))
#     # print('*'*88)

# from IPython import embed
# embed(header="Embedded interpreter at 'test_expose.py':32")
