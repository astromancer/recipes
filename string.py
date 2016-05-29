import re
import numpy as np
import functools as ft
from pprint import pformat

from .misc import getTerminalSize
from .iter import as_sequence
from myio import warn

from IPython import embed



#****************************************************************************************************    
def overlay( text, bgtext='', alignment='^', width=None ):
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


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~            
#def kill_brackets(line, brackets='()'):
    #pattern = '\s*\([\w\s]+\)'
    #return re.sub( pattern, '', line)

def kill_brackets(line, brackets='()'):
    pattern = '\([^\)]+\)'
    return re.sub(pattern, '', line)

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
def rformat( item, precision=2, pretty=True ):
    #NOTE: LOOK AT pprint
    '''
    Apply numerical formatting recursively for arbitrarily nested iterators, optionally applying a 
    conversion function on each item.
    '''
    if isinstance(item, str):
        return item
    
    if isinstance(item, (int, float)):
        return minfloatformat(item, precision)
        
    
    try:                #array-like items with len(item) in [0,1]
        #NOTE: This will suppress the type representation of the object str
        if isinstance(np.asscalar(item), str):          #np.asscalar converts np types to python builtin types (Phew!!)
            return str(item)
            
        if isinstance(np.asscalar(item), (int, float)):
            return minfloatformat(item, precision)
    except:
        #Item is not str, int, float, or convertible to such...
        pass
    
    if isinstance(item, np.ndarray):
        return np.array2string( item, 
                                precision=precision )       #NOTE:  lots more functionality here
        
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
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def as_superstrings( obj, props=(), **propkw ):
    ''' 
    Convert the obj to an array of SuperString objects, applying the properties.
    Parameters
    ----------
    obj         :       If input is unsized - return its SuperString representation
                        If input is 0 size - return empty SuperString object
                        Else return array of SuperString objects
    '''
    precision   = propkw.pop( 'precision', 2 )
    ndmin       = propkw.pop( 'ndmin', 0 )
    pretty      = propkw.pop( 'pretty', True )
    
    obja = np.array(as_sequence(obj), dtype=object )
    #try:
        #obja = np.atleast_1d(obj)
    #except Exception as err:
        #print(err)
        #from IPython import embed
        #embed()
    
    #reshape complex dtype arrays to object arrays
    if obja.dtype.kind == 'V':  #complex dtype as in record array
        #check if all the dtypes are the same.  If so we can change view
        dtypes = next(zip(*obja.dtype.fields.values()))
        dtype0 = dtypes[0]
        if np.equal(dtypes, dtype0).all():
            obja = obja.view(dtype0).reshape(len(obja), -1)
    #else:
    
    #view as object array
    #obja = obja.astype(object)
    
    if isinstance(props, dict):
        propkw.update( props )
        props = ()
    else:
        props = np.atleast_1d(props)    #as_sequence( props, return_as=tuple)
    
    #deal with empty arrays     #???????
    if not len(obja): #???????
        return SuperString(str(obj)) 
        
    fun = lambda s : SuperString( rformat(s, precision, pretty) ).set_property(*props, **propkw)
    out = np.vectorize(fun, (SuperString,))(obja)
    
    if len(out)==1 and out.ndim==1 and ndmin==0:
        out = out[0]            #collapse arrays of shape (1,) to item itself if ndmin=0 asked for
    
    return out

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def banner( *args, **props ):
    '''print pretty banner'''
    swoosh      = props.pop( 'swoosh', '=', )
    width       = props.pop( 'width', getTerminalSize()[0] )
    pretty      = props.pop( 'pretty', True )
    _print      = props.pop( '_print', True )
    
    swoosh = swoosh * width
    #TODO: fill whitespace to width?    
    #try:
    msg = '\n'.join( as_superstrings(args, ndmin=1, pretty=pretty)  )
    #except:
        #embed()
    
    #.center( width )
    info = '\n'.join( ['\n', swoosh, msg, swoosh, '\n' ] )
    
    info = as_superstrings(info).set_property( **props )
    
    if _print:
        print( info )
    
    return info
