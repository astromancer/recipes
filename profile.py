# Code profiling
import os
import sys
import inspect
import linecache
import functools

import re
import numpy as np
from itertools import starmap

from recipes.iter import pairwise, flatiter, where_true
from ansi.string import SuperString
from ansi.table import Table

from io import StringIO

from line_profiler import LineProfiler

#from IPython import embed

#class Profile(object):
    #'''Wrapper for code profiling.'''
    #def __call__(self, follow=[]):
        


#====================================================================================================
def truncate(block, maxlen, ellipses='...', fill=True):
    return ['{0:{1:d}.{1:d}}{2}'.format(l, *((maxlen-len(ellipses), ellipses) 
                                        if len(l)>maxlen else (maxlen, '')))
                for l in block]


#****************************************************************************************************
#Helper Classes
#****************************************************************************************************
def autostream(func):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        stream = args[-1]
        #print( func )
        #print( args )
        #print( kwargs )
        #print( stream )
        #print('*'*88)
        if stream is None:
            args = args[:-1] + (sys.stdout,)
        
        return func(*args, **kwargs)
    return decorated
    

class ShowFunc():
    '''Essentially a object oriented version of the native line_profiler.showfunc'''
    header_template = '{:6} {:9} {:12} {:8} {:8}  {}'
    template = '{:6} {:9} {:12} {:8} {:8.2} {}'
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, timings, unit):

        self.timings = timings
        self.unit = unit
        
        linenos, Nhits, times = zip(*timings)
        total = sum(times)
        self.total_time = total * unit
        
        self.content = {}
        for lineno, nhits, time in timings:
            per_hit = float(time) / nhits
            fraction = time / total
            self.content[lineno] = (nhits, time, per_hit, fraction)
        
        self.ignore_lines = []
        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preprocess(self):
        ''' '''
        pass
        #self.start = start_lineno
        #self.sublines = self.get_block(filename, start_lineno)
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, filename, start_lineno, func_name):
        """
        Show results for a single function.
        """
        self.start = start_lineno
        self.sublines = self.get_block(filename, start_lineno)
        self.end = self.start + len(self.sublines)
        
        self.preprocess()
        
        self.preamble(filename, func_name)
        self.header()
        #print('t'*100)
        #print( self.table )
        
        self.table()
        self.closing()
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_block(self, filename, start_lineno, strip='\n\r'):
        '''get source code block.  returns empty lines if file not accessable'''
        if not os.path.exists(filename):
            # Fake empty lines so we can see the timings, if not the code.
            nlines = max(linenos) - min(min(linenos), start_lineno) + 1
            sublines = [''] * nlines
        else:
            # Clear the cache to ensure that we get up-to-date results.
            linecache.clearcache()
            all_lines = linecache.getlines(filename)
            sublines = inspect.getblock(all_lines[start_lineno-1:])
            
            if strip:
                sublines = [l.strip(strip) for l in sublines]
        
        return sublines
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def enumerate(self):
        '''generator that enumerates code lines''' 
        i = self.start
        for line in self.sublines:
            if not i in self.ignore_lines:
                yield i, line
            i += 1
            
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @autostream
    def preamble(self, filename, func_name, stream=None):
        '''print preamble'''
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
    @autostream
    def header(self, stream=None):
        '''print header'''
        header = self.header_template.format('Line #', 'Hits', 'Time', 'Per Hit', '% Time', 'Line Contents')
        stream.write("\n")
        stream.write(header)
        stream.write("\n")
        stream.write('=' * len(header))
        stream.write("\n")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @autostream
    def table(self, stream=None):
        '''print stats'''
        empty = ('', '', '', '')
        for lineno, line in self.enumerate():
            nhits, time, per_hit, fraction = self.content.get(lineno, empty)
            percent = 100 * fraction
            txt = self.template.format(lineno, nhits, time, per_hit, percent, line)
            stream.write(txt)
            stream.write("\n")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #@autostream
    def closing(self, stream=None):
        '''print closing remarks'''
        if stream is None:
            stream= sys.stdout          #FIXME:  for some reason the @autostream decorator doesn't work here!!??
        
        stream.write("\n")
        
        
        
#****************************************************************************************************
class ShowHistogram(ShowFunc):
    '''Extend the standard profile display'''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    comment = r'\s*#'
    matcher = re.compile(comment)
    
    ellipses =  SuperString('...').set_property('r', 'bold') 
    histogram_color = 'g'
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, *args):
        super().__init__(*args)
        self.where_gaps = []
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, filename, start_lineno, func_name, **kws):
        '''
        Display profile stats
        '''
        self.docstring          = kws.get('docstring')
        self.has_docstring      = not self.docstring is None
        self.strip_docstring    = kws.get('strip_docstring',    True)
        self.strip_comments     = kws.get('strip_comments',     True)
        self.strip_blanks       = kws.get('strip_blanks',       True)
        self.condense           = kws.get('condense',           False)
        self.gap_borders        = kws.get('gap_borders',        False)
        self.truncate_lines     = kws.get('truncate_lines')
        #TODO: syntax_highlighting?????
        
        super().__call__(filename, start_lineno, func_name)
        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preprocess(self):
        ''' '''
        if self.has_docstring and self.strip_docstring:
            dl = self.docstring.count('\n') + 1
            self.ignore_lines = list(range(self.start + 1,
                                           self.start + 1 + dl))
        
        if self.strip_comments:
            ix = np.array(where_true(self.sublines, self.matcher.match))
            self.ignore_lines += list(ix+self.start)
        
        if self.strip_blanks:
            ix = np.array(where_true(self.sublines, str.isspace ))
            self.ignore_lines += list(ix+self.start)
        
        if self.condense:
            #don't print source code for sections that weren't excecuted 
            #(eg. inside if statement or nested function not followed.  Instead
            #print seperator lines to segment.
            #FIXME: single line skip printed as ellipses
            linenos = sorted( {self.start} | set(self.content.keys()) | {self.end} )
            nrpairs = np.array(list(pairwise(linenos)))
            gaps = np.subtract(*zip(*nrpairs))
            intervals = nrpairs[gaps < -2] + (1,-1)
            self.ignore_lines += list(flatiter(starmap(range, intervals)))
            self.where_gaps = nrpairs[gaps < -1][:,0]    #relative to source code line numbers
            
        #truncate and fill lines with whitespace to create block text
        maxlen = max(map(len, self.sublines))
        if self.truncate_lines:
            self.sublines = truncate(self.sublines, self.truncate_lines, self.ellipses)
        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preamble(self, filename, func_name, stream=None):

        self._preamble = stream = StringIO()
        super().preamble(filename, func_name, stream)
        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def header(self):
        pass
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #@autostream
    def table(self, stream=None):
        if stream is None:
            stream= sys.stdout          #FIXME:  for some reason the @autostream decorator doesn't work here!!??
        
                
        #print( 'TABLE', self.__class__ )
        #print( stream)
            
            
        empty = ('', '', '', '')
        table = []
        linelen = len(self.sublines[0])         #at this point all lines are the same length
        where_row_borders = [0]                 #first border after column headers
        i = 0
        for lineno, line in self.enumerate():
            nhits, time, per_hit, fraction = self.content.get(lineno, empty)
            percent = fraction*100
            if fraction:
                l = int(np.round(fraction * linelen))
                line = SuperString(line[:l]).set_property(bg=self.histogram_color) + line[l:]
            
            table.append((lineno, nhits, time, per_hit, percent, line))
            
            if lineno in self.where_gaps:
                if self.gap_borders:        #NOTE:  THIS NEGLECTS DOCSTRING GAP!!!!
                    where_row_borders.append(i+1)
                #insert blank line to indicate gap!
                table.append((self.ellipses, '', '', '', '', self.ellipses))
                i += 1
            i += 1
        
        where_row_borders.append(i)
        colhead = ('#',  'Hits', 'Time', 'Per Hit', '% Time', 'Line Contents')
        self._preamble.seek(0)
        title = self._preamble.read()
        
        self._table =  Table(table,
                             title=title,
                             title_alignment='left',
                             title_props={'text':'bold','bg':'m'},
                             col_headers=colhead,
                             col_head_props={'bg':'c'},
                             where_row_borders=where_row_borders)
        #embed()
        stream.write( str(self._table) )
        
        #embed()
        
        
#****************************************************************************************************
#Decorator class
#****************************************************************************************************        
class ProfileStatsDisplay():
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
#HistogramDisplay

class HLineProfiler(LineProfiler):
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def print_stats(self):
        lstats = self.get_stats()
        stats = lstats.timings
        unit =  lstats.unit
        
        fdict = {func.__name__ : func for func in self.functions} #NOTE: will only work for unique function names
        
        for (fn, lineno, name), timings in sorted(stats.items()):
            docstring = getattr(fdict[name], '__doc__', None)
            
            show = ShowHistogram(timings, unit)
            
            show(fn, lineno, name, 
                 #strip_docstring=True
                 #docstring=docstring, 
                 condense=True,
                 truncate_lines=80)

class HistogramDisplay(ProfileStatsDisplay):
    profiler_class = HLineProfiler
            
            
#****************************************************************************************************        
class profile():
    '''
    class that contains varioaus decorators for profiling functions with line_profiler
    '''
    def __init__(self, follow=[]):
        #print( 'initializing' )
        self.follow = follow
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self, func):
        '''Uses line_profiler native output for display.'''
        return ProfileStatsDisplay(self.follow)(func)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def histogram(self, func):
        '''Creates a ANSI histogram to indicate line excecution time'''
        return HistogramDisplay(self.follow)(func)

#TODO: profile a class and follow all its methods
