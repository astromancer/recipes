import time
import functools
import traceback
import inspect
from collections import defaultdict#, OrderedDict
from recipes.dict import DefaultOrderedDict

# TODO: class
class Chrono():
    fmt = '{: <50s} took {:s}'

    def __init__(self, title=None):
        # print(inspect.getmodule(self))
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        if title is not None:
            title = str(module)

        self.title = title or ''
        self._mark = time.time()
        self.deltas = []
        self.labels = []

        self.funcs = DefaultOrderedDict(int)#OrderedDict()
        self.hits = defaultdict(int)


    def mark(self, label=None):
        elapsed = time.time() - self._mark
        self._mark = time.time()
        if label:
            self.deltas.append(elapsed)
            self.labels.append(label)


    def report(self):
        print(self.title)
        for t, lbl in zip(self.deltas, self.labels):
            txt = self.fmt.format(lbl, fmt_hms(t))
            print(txt)

        for f, t in self.funcs.items():
            txt = self.fmt.format('Function: %s' % f.__name__, fmt_hms(t))
            print(txt)

    # def add_function(self):
    #     'TODO'
    #
    # # def register(self):
    #     """decorator to be used as
    #     @chrono.register
    #     def foo():
    #         pass
    #     """

    def timer(self, func):

        @functools.wraps(func)
        def wrapper(*args, **kw):
            ts = time.time()
            result = func(*args, **kw)
            te = time.time()

            self.hits[func] += 1
            self.funcs[func] += (te - ts)
            return result

        return wrapper


def timer(f):

    @functools.wraps(f)
    def wrapper(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        # TODO: use generic formatter as in expose.args
        # (OR pass formatter as argument)
        # TRIM items with big str reps

        # print('func:%s(%r, %r) took: %2.4f sec'
        # % (f.__name__, args, kw, te-ts))

        print('func: %s took:\t%2.4f sec'
              % (f.__name__, te - ts))
        return result

    return wrapper


def timer_extra(postscript, *psargs):
    def timer(f):
        @functools.wraps(f)
        def wrapper(*args, **kw):
            ts = time.time()
            result = f(*args, **kw)
            te = time.time()
            td = te - ts

            print('func: %s\ttook: %2.4f sec'
                  % (f.__name__, td))

            try:
                postscript(td, *psargs)
            except Exception as err:
                print('WHOOPS!')
                traceback.print_exc()

                # pass

            return result

        return wrapper

    return timer


def hms(t):
    m, s = divmod(t, 60)
    h, m = divmod(m, 60)
    return h, m, s


def first_non_zero(a):
    for i, e in enumerate(a):
        if e:
            return i


def fmt_hms(t, sep='hms'):
    if len(sep) == 1:
        sep *= 3
    sexa = hms(t)
    start = first_non_zero(sexa)
    parts = list(map('{:g}{:}'.format, sexa, sep))
    return ''.join(parts[start:])


def timer_highlight(f):
    from ansi import as_ansi
    from decor.expose import get_func_repr

    @functools.wraps(f)
    def wrapper(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        r = get_func_repr(f, args, kw, verbosity=1)
        # r = f.__name__
        print(as_ansi('Timer', txt='underline', bg='c'))
        print(as_ansi(r, bg='c'))
        print(as_ansi(fmt_hms(te - ts), bg='y'))

        return result

    return wrapper


def timer_dev(f):
    from ansi import as_ansi
    from ansi.table import Table
    from decor.expose import get_func_repr

    # TODO: methods similar to profiler: add func / print report / etc

    @functools.wraps(f)
    def wrapper(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        r = get_func_repr(f, args, kw, verbosity=1)
        tstr = as_ansi(fmt_hms(te - ts), bg='y')
        tbl = Table([r, tstr],
                    title='Timer',
                    title_props=dict(c='bold', bg='g'),
                    row_headers=['func', 'Time'],
                    where_row_borders=[0, -1])
        print(tbl)
        return result

    return wrapper






# def timer(codicil, *psargs):
# def timer(f):
# @functools.wraps(f)
# def wrapper(*args, **kw):
# ts = time.time()
# result = f(*args, **kw)
# te = time.time()
# td = te-ts

# try:
# codicil(td, *psargs)
# except Exception as err:
# import traceback
# traceback.print_exc()

# return result
# return wrapper
# return timer



# from ..expose import get_func_repr

# ====================================================================================================
# class timer(OptionalArgumentsDecorator):
#     """Print function execution time upon return"""
#
#     def make_wrapper(self, func):
#         @functools.wraps(func)
#         def wrapper(*args, **kws):
#             ts = time.time()
#             result = func(*args, **kws)
#             te = time.time()
#             self._t = te - ts
#             self._print_info(args, kws)
#             return result
#
#         return wrapper
#
#     def __call__(self, *args, **kws):
#         ts = time.time()
#         result = self.func(*args, **kws)
#         te = time.time()
#         self._t = te - ts
#         self._print_info(args, kws)
#         return result
#
#     def _print_info(self, args, kws):
#         # print timing info
#         # FIXME: may not always want such verbose output...
#         repr_ = self.get_func_repr(args, kws)
#         size = len(repr_.split('\n', 1)[0])
#         swoosh = '-' * size
#         pre = overlay('Timer', swoosh)
#         post = '\n'.join((swoosh, 'took:\t%2.4f sec' % self._t, swoosh))
#         str_ = '\n'.join((pre, repr_, post))
#         print(str_)
#         sys.stdout.flush()