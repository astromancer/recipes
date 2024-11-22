

# from recipes.decorators.tests import test_cases as tcx
# pylint: disable-all

from recipes.io import trace


def test_trace_decor():
    @trace.show
    def foo(a, b=1, *args, c=2, **kws):
        pass

    foo(88, 12, 11, c=4, y=1)


def test_trace_decor2():
    @trace.args
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
# embed(header="Embedded interpreter at 'test_trace.py':32")


# if __name__ == '__main__':
# from recipes.io.trace import TracePrints, TraceWarnings
#     sys.stdout = TracePrints()
#     print('Hello World!')
#     # restore
#     sys.stdout = sys.stdout.stdout

#     wtb = TraceWarnings()
#     warnings.warn('Dinosaurs!!')
#     # restore
#     wtb.off()
