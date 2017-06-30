'''
Decorators for code profiling / timing
'''

import os
import re
import sys
import inspect
import linecache
import functools
import traceback
import time
from itertools import starmap
from io import StringIO

import numpy as np
from line_profiler import LineProfiler

from recipes.iter import pairwise, where_true, where_false  #flatiter,
from recipes.list import flatten, find_missing_numbers
from recipes.string import overlay, matchBrackets
from ansi.str import AnsiStr
from ansi.table import Table

from .expose import get_func_repr



#TODO: profile a class and follow all its methods

#TODO: Heatmap256

#class Profile(object):
    #'''Wrapper for code profiling.'''
    #def __call__(self, follow=[]):

#====================================================================================================
# use classes to make the decorators picklable
class DecoratorBase():                              #TODO: move to __init__ of module
    '''A picklable decorator'''
    def __init__(self, func):
        self.func = func
        # Update this class to look like the wrapped function
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kws):
        # Default null decorator
        return self.func(*args, **kws)

#====================================================================================================
class timer(DecoratorBase):
    """Print function execution time upon return"""
    def __call__(self, *args, **kws):
        ts = time.time()
        result = self.func(*args, **kws)
        te = time.time()
        self._t = te - ts
        self._print_info(args, kws)
        return result

    def _print_info(self, args, kws):
        # print timing info
        #FIXME: may not always want such verbose output...
        repr_ = self.get_func_repr(args, kws)
        size = len(repr_.split('\n', 1)[0])
        swoosh = '-' * size
        pre = overlay('Timer', swoosh)
        post = '\n'.join((swoosh, 'took:\t%2.4f sec' % self._t, swoosh))
        str_ = '\n'.join((pre, repr_, post))
        print(str_)
        sys.stdout.flush()

    def get_func_repr(self, args, kws):
        return get_func_repr(self.func, args, kws)


#====================================================================================================
#TODO: add postscript option with function to evaluate after with timing values
def timer(f):
    @functools.wraps(f)
    def wrapper(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        #TODO: use generic formatter as in expose.args
        #(OR pass formatter as argument)
            #TRIM items with big str reps

        #print('func:%s(%r, %r) took: %2.4f sec'
            #% (f.__name__, args, kw, te-ts))

        print('func: %s took:\t%2.4f sec'
            % (f.__name__, te-ts))
        return result
    return wrapper


def timer_extra(postscript, *psargs):
    def timer(f):
        @functools.wraps(f)
        def wrapper(*args, **kw):
            ts = time.time()
            result = f(*args, **kw)
            te = time.time()
            td = te-ts

            print('func: %s\ttook: %2.4f sec'
                % (f.__name__, td))

            try:
                postscript(td, *psargs)
            except Exception as err:
                print('WHOOPS!')
                traceback.print_exc()

                #pass

            return result
        return wrapper
    return timer



#def timer(codicil, *psargs):
    #def timer(f):
        #@functools.wraps(f)
        #def wrapper(*args, **kw):
            #ts = time.time()
            #result = f(*args, **kw)
            #te = time.time()
            #td = te-ts

            #try:
                #codicil(td, *psargs)
            #except Exception as err:
                #import traceback
                #traceback.print_exc()

            #return result
        #return wrapper
    #return timer


#====================================================================================================
def truncateBlockGen(block, width, ellipsis='...'):
    '''Truncate a block of text at given *width* adding ellipsis to indicate missing text'''
    le = AnsiStr(ellipsis).len_no_ansi()
    for line in block:
        if len(line) > width:   # need to truncate
            yield line[:(width-le)] + ellipsis
        else:                   # fill to width with whitespace
            yield '{0:.{1:d}}'.format(line, width)


def truncateBlock(block, width, ellipsis='...'):
    return list(truncateBlockGen(block, width, ellipsis))


# def truncate(block, maxlen, ellipsis='...', fill=True):
#     tblock = []
#     fmt = '{0:{1:d}.{1:d}}{2}'
#     for line in block:
#         if len(line) > maxlen:  # need to truncate
#             l = AnsiStr(ellipsis).len_ansi()
#             ll, e = maxlen - l, ellipsis
#         else:
#             ll, e = maxlen, ''
#         tblock.append(fmt.format(line, ll, e))
#     return tblock


# def truncate(block, maxlen, ellipsis='...', fill=True):
#     return ['{0:{1:d}.{1:d}}{2}'.format(
#         l, *((maxlen - len(ellipsis), ellipsis) if len(l) > maxlen else (maxlen, ''))
#     ) for l in block]




#****************************************************************************************************
# Helper Classes
#****************************************************************************************************
#FIXME: does not reset after multiple calls.  may sometimes be desired
class ShowFunc():
    """
    Helper class that prints profiler results for a single function when called. The base class is
    essentially an object oriented (and therefore extensible) version of the native line_profiler.showfunc
    """

    column_headers = 'Line #', 'Hits', 'Time', 'Per Hit', '% Time', 'Line Contents'
    header_template = '{:6} {:9} {:12} {:8} {:8}  {}'
    template = '{:6} {:9} {:12} {:8} {:8.2} {}'

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, timings, unit):

        self.timings = timings
        self.unit = unit
        # self.stream = stream or sys.stdout

        linenos, Nhits, times = zip(*timings)       #FIXME: borks when timings == []
        self.linenos = linenos
        total = sum(times)
        self.total_time = total * unit

        self.stats = {}
        for lineno, nhits, time in timings:
            per_hit = float(time) / nhits
            fraction = time / total
            self.stats[lineno] = (nhits, time, per_hit, fraction)

        self.ignoreLines = []

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, filename, start_lineno, func, stream=None):
        """
        Show profiler results for a single function.
        """
        self.start = start_lineno
        self.sourceCodeLines = self.get_block(filename, start_lineno)
        self.end = self.start + len(self.sourceCodeLines)

        self.preprocess()

        self.preamble(filename, func.__name__, stream)
        self.header()
        #print('t'*100)
        #print( self.table )

        self.table()
        self.closing()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_block(self, filename, start_lineno, strip='\n\r'):
        '''
        Get source code block of the profiled function. Returns empty lines if file not accessible
        (e.g. profiling a function in an interactive session)
        '''
        if not os.path.exists(filename):
            # Fake empty lines so we can see the timings, if not the code.
            nlines = max(self.linenos) - min(min(self.linenos), start_lineno) + 1
            sublines = [''] * nlines
        else:
            # Clear the cache to ensure that we get up-to-date results.
            linecache.clearcache()
            all_lines = linecache.getlines(filename)
            sublines = inspect.getblock(all_lines[start_lineno-1:])

            #TODO: OR inspect.getsourcelines()

            if strip:
                sublines = [l.strip(strip) for l in sublines]

        return sublines

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preprocess(self):
        """Potentially implemented in subclass to preprocess the raw source code lines for display """
        pass
        #self.start = start_lineno
        #self.sourceCodeLines = self.get_block(filename, start_lineno)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def enumerate(self):
        """generator that enumerates code lines filtering those in `ignoreLines`"""
        i = self.start
        for line in self.sourceCodeLines:
            if not i in self.ignoreLines:
                yield i, line
            i += 1

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preamble(self, filename, func_name, stream=None):
        """print preamble"""
        stream = stream or sys.stdout
        stream.write("File: %s\n" % filename)
        stream.write("Function: %s at line %s\n" % (func_name, self.start))
        stream.write("Total time: %g s\n" % self.total_time)

        if not os.path.exists(filename):
            stream.write("\n")
            stream.write("Could not find file %s\n" % filename)
            stream.write("Are you sure you are running this program from the same directory\n")
            stream.write("that you ran the profiler from?\n")
            stream.write("Continuing without the function's contents.\n")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def header(self, stream=None):
        """print header"""
        stream = stream or sys.stdout
        #TODO: add time unit (ms)??
        header = self.header_template.format(self.column_headers)
        stream.write("\n")
        stream.write(header)
        stream.write("\n")
        stream.write('=' * len(header))
        stream.write("\n")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def table(self, stream=None):
        """print stats table"""
        stream = stream or sys.stdout
        empty = ('', '', '', '')
        for lineno, line in self.enumerate():
            nhits, time, per_hit, fraction = self.stats.get(lineno, empty)
            percent = 100 * fraction
            txt = self.template.format(lineno, nhits, time, per_hit, percent, line)
            stream.write(txt)
            stream.write("\n")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def closing(self, stream=None):
        """print closing remarks"""
        stream = stream or sys.stdout
        stream.write("\n")



#****************************************************************************************************
class ShowHistogram(ShowFunc):
    """
    Extend the standard profile display with multiple options for how to format the returned source
    code body based on the profiling statistics.
    """
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    comment = r'\s*#'       # match only whitespace followed by comment #
    commentMatcher = re.compile(comment)

    ellipsis = AnsiStr('...').set_property('r', 'bold')
    histogram_color = 'g'
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, *args):
        super().__init__(*args)
        self.where_gaps = []

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, filename, start_lineno, func, **kws):
        """
        Display profile stats

        :param filename:
        :param start_lineno:
        :param func:
        :param kws:
        :return:
        """
        strip = set(kws.get('strip', ('#', '', '"""', 0)))
        docInd = ('"""',  "'''", 'doc', 'docstring')   # any of these can be passed to strip docstring
        commentInd = ('#', 'comment', 'comments')
        blankInd = ('', ' ', 'blank')
        zeroInd = (0, '0', 'zero', 'zeros')
        # TODO:  small ?

        self.docstring = inspect.getdoc(func)
        self.has_docstring = self.docstring is not None
        self.strip_docstring = bool(set(docInd) & strip)
        self.strip_comments = bool(set(commentInd) & strip)
        self.strip_blanks = bool(set(blankInd) & strip)
        self.strip_zeros = bool(set(zeroInd) & strip)

        self.condense           = False #kws.get('condense',           False)
        self.gap_borders        = kws.get('gap_borders',        False)
        self.truncate_width     = kws.get('truncate_width')     # MaxLineWidth
        #TODO: syntax_highlighting?????

        super().__call__(filename, start_lineno, func)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preprocess(self):
        """"""
        ignore = []

        # Make sure we do not ignore the function `def` line (which may be preceded by decorators)
        raw = '\n'.join(self.sourceCodeLines)
        argStr, ix = matchBrackets(raw)
        funcStartIx = raw[:ix[1]].count('\n') + 1       # either docstring or function body starts here
        funcStartIx += self.start                       # source code relative
        if self.has_docstring and self.strip_docstring:
            docSize = self.docstring.count('\n') + 1    # number of lines in docstring
            ignore += list(range(funcStartIx,  funcStartIx + docSize))

        if self.strip_comments:
            ix = np.array(where_true(self.sourceCodeLines, self.commentMatcher.match))
            ignore += list(ix + self.start)

        if self.strip_blanks:
            ixBlank = where_true(self.sourceCodeLines, str.isspace)  # only whitespace
            ixEmpty = where_false(self.sourceCodeLines)              # empty lines
            ix = np.array(ixEmpty + ixBlank) + self.start            # indices relative to source code
            ignore += list(ix)

        if self.strip_zeros:
            linenos = sorted({funcStartIx, self.end} | set(self.stats.keys()))
            ixNoStats = find_missing_numbers(linenos) # no timing stats available for these lines (i.e. they where not executed
            ignore += ixNoStats

        # if self.strip_small:
        #     ixLine, data = zip(*self.stats.items())
        #     *stuff, fractions = zip(*data)
        #     tolerance = 1e-5
        #     ix = np.array(ixLine)[np.less(fractions, tolerance)]
        #     ignore += list(ix)

        # remove isolated lines from ignore list
        # If we are inserting ellipsis to indicate missing blocks, it's useless to do so for a single skipped line
        ignore = sorted(set(ignore))
        if len(ignore) > 1:
            singleSkip = np.diff(ignore) == 1 # isolated ignore lines.
            wms = np.where(~singleSkip)[0]
            splitBlockIx = np.split(ignore, wms + 1)
            skipBlockSize = np.vectorize(len)(splitBlockIx)
            ix = np.take(splitBlockIx, np.where(skipBlockSize == 1))
            ignore = list(set(ignore) - set(flatten(ix)))
            # ignore now contains only indices of continuous multiline code blocks to skip when printing

            # figure out where the gaps are in the displayed code so we can indicate gaps with ellipsis
            lineIxShow = set(range(self.start, self.end)) - set(ignore)
            nrpairs = np.array(list(pairwise(lineIxShow)))
            gaps = np.subtract(*zip(*nrpairs))
            self.where_gaps = nrpairs[gaps < -1][:, 0]  # relative to source code line numbers
        else:
            ignore = []

        self.ignoreLines = ignore
        # truncate and fill lines with whitespace to create block text
        if self.truncate_width:
            self.sourceCodeLines = truncateBlock(self.sourceCodeLines, self.truncate_width,
                                                 self.ellipsis)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preamble(self, filename, func_name, stream=None):
        # intercept the preamble text so we can use it as a table header
        self._preamble = StringIO()
        super().preamble(filename, func_name, self._preamble)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def header(self, stream=None):
        # for the table we need tuple of headers not formatted str, so pass
        pass

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def table(self, stream=None):
        """make the time table and write to stream"""
        stream = stream or sys.stdout

        empty = ('', '', '', '')
        table = []
        # self.truncate_width
        linelen = len(self.sourceCodeLines[0])  # at this point all lines are the same length
        where_row_borders = [0]  # first border after column headers
        i = 0

        for lineno, line in self.enumerate():
            nhits, time, per_hit, fraction = self.stats.get(lineno, empty)
            percent = fraction * 100
            if fraction:
                l = int(np.round(fraction * linelen))
                line = AnsiStr(line[:l]).set_property(bg=self.histogram_color) + line[l:]

            table.append((lineno, nhits, time, per_hit, percent, line))

            # print seperator lines to segment code blocks
            if lineno in self.where_gaps:
                if self.gap_borders:
                    where_row_borders.append(i + 1)
                # insert blank line to indicate gap!
                table.append((self.ellipsis, '', '', '', '', self.ellipsis))
                i += 1
            i += 1

        where_row_borders.append(i)
        colhead = list(self.column_headers)
        colhead[0].strip('Line ')  # to save some space in the table
        self._preamble.seek(0)
        title = self._preamble.read()

        self._table = Table(table,
                            title=title,
                            title_align='left',
                            title_props={'text': 'bold', 'bg': 'm'},
                            col_headers=colhead,
                            col_head_props={'bg': 'c'},
                            where_row_borders=where_row_borders)

        stream.write(str(self._table))



#****************************************************************************************************
#Decorator class
#****************************************************************************************************
class ProfileStatsDisplay():
    """
    Decorator for printing results from multiple profiled functions
    """
    profiler_class = LineProfiler
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, follow=[]):
        self.profiler = self.profiler_class()
        self.follow = follow

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, func):
        #----------------------------------------------------------------------------------------------------
        @functools.wraps(func)
        def profiled_func(*args, **kwargs):
            try:
                self.profiler.add_function(func)
                for f in self.follow:
                    self.profiler.add_function(f)
                self.profiler.enable_by_count()
                return func(*args, **kwargs)
            finally:
                self.profiler.print_stats()
        #----------------------------------------------------------------------------------------------------
        return profiled_func

#except ImportError:
    #def do_profile(follow=[]):
        #"Helpful if you accidentally leave in production!"
        #def inner(func):
            #def nothing(*args, **kwargs):
                #return func(*args, **kwargs)
            #return nothing
        #return inner

#****************************************************************************************************
class HLineProfiler(LineProfiler):
    """
    Subclass of LineProfiler with custom print_stats method
    """
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def print_stats(self, stream=None, stripzeros=False):

        lstats = self.get_stats()
        stats = lstats.timings
        unit = lstats.unit

        # Get function names
        fdict = {func.__name__: func for func in self.functions}
        # FIXME: does not work for decorated functions
        # NOTE: will only work for unique function names

        for (fn, lineno, name), timings in sorted(stats.items()):
            if len(timings):
                show = ShowHistogram(timings, unit)
                show(fn, lineno, fdict[name],
                     strip=('', '#', '"""', 0),
                     truncate_width=100)
            else:
                print('%s not executed' % name)

        #TODO: Optionally display top 10 most expensive lines...


class HistogramDisplay(ProfileStatsDisplay):
    profiler_class = HLineProfiler
    # NOTE: alternatively, have this definition in profile class below??






def get_methods(cls_or_obj):
    import inspect
    names, methods = zip(*inspect.getmembers(cls_or_obj, predicate=inspect.ismethod))
    return methods
