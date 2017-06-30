'''
Decorators for code profiling / timing
'''

import os
import re
import sys
import inspect
import linecache
# import functools
# import traceback
# import time
# from itertools import starmap
from io import StringIO

import numpy as np


from recipes.iter import pairwise, where_true, where_false  #flatiter,
from recipes.list import flatten, find_missing_numbers
from recipes.string import overlay, matchBrackets
# from ansi.str import AnsiStr
import ansi
from ansi.table import Table

#TODO: profile a class and follow all its methods

#TODO: Heatmap256

#====================================================================================================
def truncateBlockGen(block, width, ellipsis='...'):
    '''Truncate a block of text at given *width* adding ellipsis to indicate missing text'''
    le = ansi.len_bare(ellipsis)
    for line in block:
        if len(line) > width:   # need to truncate
            yield line[:(width-le)] + ellipsis
        else:                   # fill to width with whitespace
            yield '{0:.{1:d}}'.format(line, width)


def truncateBlock(block, width, ellipsis='...'):
    return list(truncateBlockGen(block, width, ellipsis))


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

        lineNos, Nhits, times = zip(*timings)       #FIXME: borks when timings == []
        self.lineNos = lineNos
        total = sum(times)
        self.total_time = total * unit

        self.stats = {}
        for lineNo, nhits, time in timings:
            per_hit = float(time) / nhits
            fraction = time / total
            self.stats[lineNo] = (nhits, time, per_hit, fraction)

        self.ignoreLines = []

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, filename, start_lineNo, func, stream=None):
        """
        Show profiler results for a single function.
        """
        self.start = start_lineNo
        self.sourceCodeLines = self.get_block(filename, start_lineNo)
        self.end = self.start + len(self.sourceCodeLines)

        self.preprocess()

        self.preamble(filename, func.__name__, stream)
        self.header()
        #print('t'*100)
        #print( self.table )

        self.table()
        self.closing()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_block(self, filename, start_lineNo, strip='\n\r'):
        '''
        Get source code block of the profiled function. Returns empty lines if file not accessible
        (e.g. profiling a function in an interactive session)
        '''
        if not os.path.exists(filename):
            # Fake empty lines so we can see the timings, if not the code.
            nlines = max(self.lineNos) - min(min(self.lineNos), start_lineNo) + 1
            sublines = [''] * nlines
        else:
            # Clear the cache to ensure that we get up-to-date results.
            linecache.clearcache()
            all_lines = linecache.getlines(filename)
            sublines = inspect.getblock(all_lines[start_lineNo-1:])

            #TODO: OR inspect.getsourcelines(func)

            if strip:
                sublines = [l.strip(strip) for l in sublines]

        return sublines

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preprocess(self):
        """Potentially implemented in subclass to preprocess the raw source code lines for display """
        pass
        #self.start = start_lineNo
        #self.sourceCodeLines = self.get_block(filename, start_lineNo)

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
        for lineNo, line in self.enumerate():
            nhits, time, per_hit, fraction = self.stats.get(lineNo, empty)
            percent = 100 * fraction
            txt = self.template.format(lineNo, nhits, time, per_hit, percent, line)
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

    ellipsis = ansi.codes.apply('...', 'r', 'bold')
    histogram_color = 'g'
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, *args):
        super().__init__(*args)
        self.where_gaps = []

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, filename, start_lineNo, func, **kws):
        """
        Display profile stats

        :param filename:
        :param start_lineNo:
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

        super().__call__(filename, start_lineNo, func)

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
            lineNos = sorted({funcStartIx, self.end} | set(self.stats.keys()))
            ixNoStats = find_missing_numbers(lineNos) # no timing stats available for these lines (i.e. they where not executed
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
            skipBlockSize = np.array(list(map(len, splitBlockIx))) # np.vectorize(len)(splitBlockIx)
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

        for lineNo, line in self.enumerate():
            nhits, time, per_hit, fraction = self.stats.get(lineNo, empty)
            percent = fraction * 100
            if fraction:
                l = int(np.round(fraction * linelen))
                bar = ansi.codes.apply(line[:l], bg=self.histogram_color)
                line = bar + line[l:]

            table.append((lineNo, nhits, time, per_hit, percent, line))

            # print seperator lines to segment code blocks
            if lineNo in self.where_gaps:
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
                            where_row_borders=where_row_borders,
                            precision=2, minimalist=True)

        stream.write(str(self._table))

