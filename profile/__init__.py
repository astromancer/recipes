# FIXME: structure is cumbersome. rethink. Decorators / profilers should be more distinct

import functools
import inspect

from line_profiler import LineProfiler

from .printers import ShowHistogram
from ..base import OptionalArgumentsDecorator


# ====================================================================================================
def get_methods(cls_or_obj):
    import inspect
    names, methods = zip(*inspect.getmembers(cls_or_obj, predicate=inspect.ismethod))
    return methods


# ****************************************************************************************************
# Decorator class
# ****************************************************************************************************
class ProfileStatsDisplay(OptionalArgumentsDecorator):
    """
    Decorator for printing results from multiple profiled functions
    """
    profiler_class = LineProfiler

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def setup(self, follow=None, **kws):
        # TODO: stream argument
        self.follow = [] if follow is None else follow
        self.profiler = self.profiler_class()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def make_wrapper(self, func):
        # functools.update_wrapper(self, func)
        # ----------------------------------------------------------------------------------------------------
        @functools.wraps(func)
        def profiled_func(*args, **kwargs):
            # print(func, args, kwargs)
            try:
                self.profiler.add_function(func)
                for f in self.follow:
                    self.profiler.add_function(f)
                self.profiler.enable_by_count()
                return func(*args, **kwargs)
            finally:
                self.profiler.print_stats()

        # ----------------------------------------------------------------------------------------------------
        return profiled_func

        # except ImportError:
        # def do_profile(follow=[]):
        # "Helpful if you accidentally leave in production!"
        # def inner(func):
        # def nothing(*args, **kwargs):
        # return func(*args, **kwargs)
        # return nothing
        # return inner


# ****************************************************************************************************
class HLineProfiler(LineProfiler):
    """
    Subclass of LineProfiler with custom print_stats method
    """

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def print_stats(self, stream=None, stripzeros=False):   # TODO: rename report??

        lstats = self.get_stats()
        stats = lstats.timings
        unit = lstats.unit

        # Get function names
        fdict = {func.__name__: func for func in self.functions}
        # FIXME: does not work for decorated functions
        # NOTE: will only work for unique function names

        not_run = []
        for (filename, lineno, name), timings in stats.items():  # TODO: sort most expensive first?
            if len(timings):
                show = ShowHistogram(timings, unit)
                show(filename, lineno, fdict[name],
                     strip=('', '#', '"""', 0),
                     truncate_width=100)
            else:
                not_run.append(name)

        if not_run:
            print('\nThe following functions where not executed:\n%s' % '\n'.join(not_run))

            # TODO: Optionally display top 10 most expensive lines...

    def rank_functions(self):
        import numpy as np
        from recipes.list import sortmore
        from ansi.str import AnsiStr
        from ansi.table import Table
        from recipes.misc import getTerminalSize

        lstats = self.get_stats()
        totals = {}
        for (filename, lineno, name), timings in lstats.timings.items():
            if len(timings):
                linenos, Nhits, times = zip(*timings)
                totals[name] = sum(times)

        totals, names = sortmore(totals.values(), totals.keys(), order=-1)
        # do histogram thing
        frac = np.divide(totals, max(totals))

        # format totals with space as thousands separator for readability
        fmtr = lambda s: '{:,}'.format(s).replace(',', ' ')
        totals = list(map(fmtr, totals))
        table = Table(list(zip(names, totals)),
                      col_headers=('Function', u'Time (\u00B5s)'))

        hwidth = getTerminalSize()[0] - table.get_width() - 1
        frac = np.round(frac * hwidth).astype(int)
        sTable = str(table).split('\n')
        bg = ShowHistogram.histogram_color
        for i, f in enumerate(frac):
            hline = AnsiStr(' ' * f).set_property(bg=bg)
            sTable[i + 2] += hline
        htable = '\n'.join(sTable)
        print(htable)


# ****************************************************************************************************
class HistogramDisplay(ProfileStatsDisplay):
    """
    Decorator that displays a highlighted version of the source code in the terminal
    to indicate execution times in a fashion that resembles a histogram. Higlighting
    is done using ANSI escape sequences. This class is not really intended to use
    directly, but can be as shown in the example below.

    example
    -------
    @profiler.histogram
    def foo():
        ...

     """
    profiler_class = HLineProfiler


# class ProfileAll(OptionalArgumentsDecorator):
#     #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def setup(self, decorator=, **kws):
#         # HACK: in order for docstrings to be visible in the convenience class *profiler* below this will
#         # HACK: need to become an __init__ ......
#         self.printerClass = HistogramDisplay
#         # self.exclude = [] if exclude is None else exclude
#
#     #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def make_wrapper(self, cls):
#         if self.decorator:
#             from decor.utils import decorateAll
#             return decorateAll(self.printerClass)(cls)
#         return cls

def profileAll(profilerClass=HLineProfiler, exclude=None):
    """
    A decorator that profiles all methods in a class.
    """
    # NOTE: there may already be existing methods in line_profiler to do this...??
    import atexit
    profiler = profilerClass()
    exclude = [] if exclude is None else exclude

    def wrapper(cls):
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name in exclude:
                profiler.add_function(method)
        profiler.enable_by_count()
        return cls

    def print_stats():
        profiler.print_stats()

    atexit.register(print_stats)

    return wrapper


# ****************************************************************************************************
class profiler(ProfileStatsDisplay):
    """
    convenience class that contains various decorators for profiling functions with line_profiler

    example
    -------
    @profile        # FIXME: this doesn't actually work yet!
    def foo():
        ...

    @profile.histogram      # FIXME: this doesn't actually work yet!
    def foo():
        ...
    """

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # histogram = HistogramDisplay
    all = profileAll

    @property
    def histogram(self):
        return HistogramDisplay

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # TODO
        # def heatmap(self, func):
        #     """Creates a ANSI 256 colour heatmap to indicate line excecution time"""
        #     return HistogramDisplay(self.follow)(func)

        # TODO:
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # def all(self, cls):
        #     # profile all methods in the class
        #     if not inspect.isclass(cls):
        #         raise ValueError('Class please')
        #
        #     from decor.profile import HLineProfiler
        #     profiler = HLineProfiler()
        #
        #     for name, method in inspect.getmembers(DragMachinery, predicate=inspect.isfunction):
        #         profiler.add_function(method)
        #     profiler.enable_by_count()
