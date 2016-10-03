import re
import numpy as np
import functools as ft
from pprint import pformat

from .misc import getTerminalSize
from .iter import as_sequence
#from recipes.str import minlogfmt
#from myio import warn

#from IPython import embed

#****************************************************************************************************    
def overlay(text, bgtext='', alignment='^', width=None):
    #TODO: verbose alignment name conversions
    '''overlay text on bgtext using given alignment.'''
    
    if not (bgtext or width):                   #nothing to align on
        return text
    
    if not bgtext:
        bgtext = ' '*width                      #align on clear background
    elif not width:
        width = len(bgtext)
    
    if len(bgtext) < len(text):                 #pointless alignment
        return text
    
    #do alignment
    if alignment == '<':                        #left aligned
        overlayed = text + bgtext[len(text):]
    elif alignment == '>':                      #right aligned
        overlayed = bgtext[:-len(text)] + text
    elif alignment == '^':                      #center aligned
        div, mod = divmod( len(text), 2 )
        pl, ph = div, div+mod
        
        idx = width//2-pl, width//2+ph                    #start and end indeces of the text in the center of the progress indicator
        overlayed = bgtext[:idx[0]] + text + bgtext[idx[1]:]                #center text in bar
    
    return overlayed 

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def rreplace(s, subs, repl):
    ''' recursively replace all the characters / sub-strings in subs with the character / string in repl.
        subs        :       characters / sub-strings to replace
                            if string               - replace all characters in string with repl
                            if sequence of strings  - replace each string with repl
    '''
    
    subs = list(subs)
    while len(subs):
        ch = subs.pop(0)
        s = s.replace( ch, repl )

    return s
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def minfloatformat(n, precision=1):
    '''minimal numeric representation of floats with given precision'''
    return '{:g}'.format(round(n, precision))
minfloatfmt = minfloatformat

def minlogformat(x, prec=2, multsym=r'\times'):
    if x==0:
        return 0
    s = np.sign(x)
    xus = abs(x)
    lx = np.log10(xus)
    pwr = np.floor(lx)
    val = s * xus * 10**-pwr
    sval = minfloatformat(val, prec)
    if sval == '1':
        return r'$10^{%i}$' % pwr
    return r'$%s%s10^{%i}$' % (sval, multsym, pwr)
minlogfmt = minlogformat

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~            
def kill_brackets(line):
    pattern = '\s*\([\w\s]+\)'
    return re.sub( pattern, '', line)


#def rmap(func, *args):
    #for a in args:
        #if np.iterable(item) and not isinstance(item, str):
            #map(func, item)
        #else:
            #func(item)
            
            
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def mapformat(fmt, func, *args):
    return fmt.format( *map(func, flatten(args)) )
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def rformat(item, precision=2, pretty=True):
    #NOTE: LOOK AT pprint
    '''
    Apply numerical formatting recursively for arbitrarily nested iterators, 
    optionally applying a conversion function on each item.
    '''
    if isinstance(item, str):
        return item
    
    if isinstance(item, (int, float)):
        return minfloatformat(item, precision)
        
    try:                #array-like items with len(item) in [0,1]
        #NOTE: This will suppress the type representation of the object str
        if isinstance(np.asscalar(item), str):
            #np.asscalar converts np types to python builtin types (Phew!!)
            return str(item)
            
        if isinstance(np.asscalar(item), (int, float)):
            return minfloatformat(item, precision)
    except:
        #Item is not str, int, float, or convertible to such...
        pass
    
    if isinstance(item, np.ndarray):
        return np.array2string(item, precision=precision)
        #NOTE:  lots more functionality here
        
    return pformat(item)
    
    #brackets = { tuple : '()', set : '{}', list : '[]' }
    #if np.iterable(item):
        
        #if isinstance(item, (tuple, set, list)):
            #br = list(brackets[type(item)])
        #else:
            #warn( 'NEED FMT FOR: {}'.format(type(item)) )
            #br = '[]'        #SEE ALSO:  np.set_print_options
        
        #recur = ft.partial(rformat, precision=precision)         #this way it works with iterators that have no __len__
        #return ', '.join( map(recur, item) ).join(br)
    
    #else:       #not str, int, float, or iterable
        #return str(item)
