import re
import numpy as np
# import functools as ft
from pprint import pformat

# from .misc import getTerminalSize
# from .iter import as_sequence
#from recipes.str import minlogfmt
#from myio import warn

#from IPython import embed

#****************************************************************************************************
def overlay(text, bgtext='', alignment='^', width=None):
    #TODO: verbose alignment name conversions. see ansi.table.get_alignment
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
        div, mod = divmod(len(text), 2)
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

def wrap(s, wrappers):
    if isinstance(wrappers, str):
        return wrappers + s + wrappers
    elif np.iterable(wrappers):
        return s.join(wrappers)

def stripNonAscii(s):
    return ''.join([x for x in s if ord(x) < 128])


# def center(self, width, fill=' ' ):

    # div, mod = divmod( len(self), 2 )
    # if mod: #i.e. odd window length
    # pl, ph = div, div+1
    # else:  #even window len
    # pl = ph = div

    # idx = width//2-pl, width//2+ph                    #start and end indeces of the text in the center of the progress indicator
    # s = fill*width
    # return s[:idx[0]] + self + s[idx[1]:]                #center text


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def minfloatformat(n, precision=1):
    '''minimal numeric representation of floats with given precision'''
    return '{:g}'.format(round(n, precision))
minfloatfmt = minfloatformat


def minlogformat(x, prec=2, multsym=r'\times'):
    if x == 0:
        return 0
    s = np.sign(x)
    xus = abs(x)
    lx = np.log10(xus)
    pwr = np.floor(lx)

    if abs(pwr) < prec:
        return minfloatformat(x, prec)

    val = s * xus * 10 ** -pwr
    valstr = minfloatformat(val, prec)
    # print(xus, pwr, val, sval)

    if valstr == '1':
        return r'$10^{%i}$' % pwr
    return r'$%s%s10^{%i}$' % (valstr, multsym, pwr)

minlogfmt = minlogformat

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def kill_brackets(line):
    pattern = '\s*\([\w\s]+\)'
    return re.sub( pattern, '', line)


def matchBrackets(s, brackets='()', return_index=True):
    """
    Find matching closed brackets.  Will return first closed pair if s contains multiple closed
    bracket pairs.

    :param s:
    :param brackets:
    :param return_index: return the indices where the brackets where found
    :return:

    example
    -------
    In [23]: matchBrackets('def sample(args=(), **kws):')
    Out[23]: 'args=(), **kws'
    """
    left, right = brackets
    if left in s:
        pre, match = s.split(left, 1)
        open_ = 1
        for index in range(len(match)):
            if match[index] in brackets:
                open_ += [1, -1][int(match[index] == right)]
            if not open_:
                if return_index:
                    return match[:index], (len(pre), len(pre) + index + 1)
                return match[:index]


#def rmap(func, *args):
    #for a in args:
        #if np.iterable(item) and not isinstance(item, str):
            #map(func, item)
        #else:
            #func(item)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def mapformat(fmt, func, *args):
    return fmt.format(*map(func, flatten(args)))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def rformat(item, precision=2, minimalist=True):
    #NOTE: LOOK AT pprint
    '''
    Apply numerical formatting recursively for arbitrarily nested iterators,
    optionally applying a conversion function on each item.

    minimalist - (bool) whether to include non-significant decimals in the float representation
                if True, will always show to given precision.
                    eg. with precision=5: 7.0001 => 7.00010
                if False, show numbers in the shortest possible format given precision.
                    eg. with precision=3: 7.0001 => 7
    '''
    if isinstance(item, str):
        return item

    floatFormatFunc = minfloatfmt if minimalist else '{:.{}f}'.format
    if isinstance(item, (int, float)):
        return floatFormatFunc(item, precision)

    try:
        # Handle array-like items with len(item) in [0,1] here
        # np.asscalar converts np types to python builtin types (Phew!!)
        # NOTE: This will suppress the type representation of the object str
        if isinstance(np.asscalar(item), str):
            return str(item)

        if isinstance(np.asscalar(item), (int, float)):
            return floatFormatFunc(item, precision)
            # NOTE: this suppresses non-significant decimals, which we do sometimes want displayed
    except:
        #Item is not str, int, float, or convertible to such...
        pass

    if isinstance(item, np.ndarray):
        return np.array2string(item, precision=precision)
        #NOTE:  lots more functionality here

    return str(item)
    # return pformat(item)

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
