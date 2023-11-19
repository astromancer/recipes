# std
import time
import inspect
import functools
from collections import defaultdict

# relative
from .. import pprint
from ..dicts import DefaultOrderedDict
from .base import Decorator


class count_calls(Decorator):
    def __init__(self, start=0, increment=1):
        self.count = start
        self.increment = increment

    def __wrapper__(self, func, *args, **kws):
        try:
            return func(*args)
        except Exception as err:
            raise err from None
        else:
            self.count += self.increment


# alias
count = count_calls


class Chrono:
    # TODO: Singleton so it can be used across multiple modules
    fmt = '{: <50s}{:s}'

    def __init__(self, title=None):
        # print(inspect.getmodule(self))
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        if title is not None:
            title = str(module)

        self.title = title or ''
        self._start = self._mark = time.time()
        self.deltas = []
        self.labels = []

        self.funcs = DefaultOrderedDict(int)  # OrderedDict()
        self.hits = defaultdict(int)

    def mark(self, label=None):
        elapsed = time.time() - self._mark
        self._mark = time.time()
        if label:
            self.deltas.append(elapsed)
            self.labels.append(label)

    def report(self):

        # TODO: multiline text block better?
        # TODO: spacing for timing values based on magnitude
        # FIXME: time format does not always pad zeros correctly

        total = time.time() - self._start
        border = '=' * 80
        hline = '-' * 80
        print()
        print(border)
        print(f'{self.__class__.__name__} Report: {self.title}')
        print(hline)
        for t, lbl in zip(self.deltas, self.labels):
            txt = self.fmt.format(lbl, pprint.hms(t))
            print(txt)

        for f, t in self.funcs.items():
            txt = self.fmt.format(f'Function: {f.__name__}', pprint.hms(t))
            print(txt)

        print(hline)
        print(self.fmt.format('Total:', pprint.hms(total)))
        print(border)

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


def timer(Decorator):
    # def __init__(self, )

    #     """Print function execution time upon return"""
    # TODO: methods similar to profiler: add func / print report / etc

    def __wrapper__(self, func, *args, **kw):
        ts = time.time()
        result = func(*args, **kw)
        te = time.time()

        # TODO: use generic formatter as in expose.args
        # (OR pass formatter as argument)
        # TRIM items with big str reps

        # print('func:%s(%r, %r) took: %2.4f sec'
        # % (f.__name__, args, kw, te-ts))

        print(f'func: {func.__name__} took:\t{te - ts:2.4f} sec')
        return result


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


# class timer_highlight(timer):
#     from decor.expose import get_func_repr

#     def _print_info(self, args, kws):

#         r = get_func_repr(f, args, kw, verbosity=1)
#         # r = f.__name__
#         print(codes.apply('Timer', txt='underline', bg='c'))
#         print(codes.apply(r, bg='c'))
#         print(codes.apply(pprint.hms(te - ts), bg='y'))

#         return result

#     return wrapper


# class timer_table(f):
#     from motley.table import Table
#     from decor.expose import get_func_repr
#
#     def _print_info(self, args, kws):
#         r = get_func_repr(f, args, kw, verbosity=1)
#         tstr = codes.apply(pprint.hms(te - ts), bg='y')
#         tbl = Table([r, tstr],
#                     title='Timer',
#                     title_style=dict(c='bold', bg='g'),
#                     row_headers=['func', 'Time'],
#                     where_row_borders=[0, -1])
#         print(tbl)
#         return result

#     return wrapper


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
