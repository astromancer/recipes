from collections import Iterable
import itertools as itt
#import functools

##########################################################################################################################################   
# Iterator functions
##########################################################################################################################################   
#TODO: Wrapper class which Implements a .list method

#====================================================================================================        
def as_iter(obj, exclude=(str,), return_as=list):
    '''
    Converts the input object to an iterable. 
    exclude     : objects that will not be considered iterables.
    return_as   : specified type to convert the object to'''
    if exclude is None: 
        exclude=()
    
    if isinstance(obj, exclude) or not isinstance(obj, Iterable):
        return return_as([obj])
    else:
        return obj
 
#alias
as_sequence = as_iter
#as_sequence_unless_str

#====================================================================================================
def flatiter(items):
    '''generator that flattens an iterator with arbitrary nesting'''
    for item in items:
        if isinstance(item, (str, bytes)):         #catches the infinite recurence resulting from character-string duality
            yield item
        else:
            try:
                for i in flatiter(item):
                    yield i
            except TypeError:
                yield item

#def flatiter(*items):
    #'''generator that flattens an iterator with arbitrary nesting'''
    #for item in items:
        #if isinstance(item, (str, bytes)):         #catches the infinite recurence resulting from character-string duality
            #yield item
        #else:
            #try:
                #for i in flatiter(item):
                    #yield i
            #except TypeError:
                #yield item

#def flatiter(*items, maxdepth=None):
    #'''
    #Generator that flattens an iterator with arbitrary nesting. 
    #Optionally provide maximum depth to flatten to.
    #'''
    #if maxdepth is None:
        #yield from _flatiter(items)
    #else:
        #def _flatit(item, depth):
            #if depth >= maxdepth:
                #yield item
            #elif isinstance(item, (str, bytes)):
                #yield item
            #else:
                #yield from _flatit(l, depth+1)
        
        #yield from _flatit(l, 0)

#====================================================================================================
def interleave(*its, **kw):
    '''interleaves two Iterables.'''
    return_as = kw.get( 'return_as', list )
    if 'fill' in kw:
        zipper = ft.partial(itt.zip_longest, fillvalue=kw['fill'])
    else:
        zipper = zip
    return return_as( [val for items in zipper(*its) for val in items] )

#====================================================================================================
def itersplit(L, idx):
    '''Split a list into sublists at the given indices'''
    return map(L.__getitem__, itt.starmap(slice, pairwise(idx)))

#====================================================================================================        
def cycleN( obj, N ):
    cyc = itt.cycle( obj )
    for i in range(N):
        yield next(cyc)

#====================================================================================================
def cycle_or_repeat(obj, N):
    '''An iterable that returns up to N items from the object if is an iterable,
        else yields the object N times.'''
    return cycleN(as_iter(obj), N)

#====================================================================================================
def take(n, iterable):
    '''Return first n items of the iterable as a list'''
    return itt.islice(iterable, n)

#====================================================================================================
def tabulate(function, start=0):
    '''Return function(0), function(1), ...'''
    return map(function, itt.count(start))

#def mapslice(function, it
    
#====================================================================================================
def tail(n, iterable):
    '''Return an iterator over the last n items'''
    # tail(3, 'ABCDEFG') --> E F G
    return iter(coll.deque(iterable, maxlen=n))

#====================================================================================================
def consume(iterator, n):
    '''Advance the iterator n-steps ahead. If n is none, consume entirely.'''
    # Use functions that consume iterators at C speed.
    if n is None:
        # feed the entire iterator into a zero-length deque
        coll.deque(iterator, maxlen=0)
    else:
        # advance to the empty slice starting at position n
        next(itt.islice(iterator, n, n), None)

#====================================================================================================
def nth(iterable, n, default=None):
    '''Returns the nth item or a default value'''
    return next(itt.islice(iterable, n, None), default)

def nthzip(n, *its):
    '''Return the nth component of the zipped sequence'''
    return tuple( nth(it, n) for it in its )

#====================================================================================================
def zipslice(start, stop, step, *its):
    '''Returns a slice of the zipped sequence of iterators'''
    return zip(*itt.islice(zip(*its), start, stop, step))
    
def zipapp(zipped, apper):
    '''Appends elements from iterator to the items in a zipped sequence.'''
    return [zpd+(app,) for (zpd,app) in zip(zipped, apper)]
 
#====================================================================================================
def quantify(iterable, pred=bool):
    '''Count how many times the predicate is true'''
    return sum(map(pred, iterable))

#====================================================================================================
def padnone(iterable):
    """Returns the sequence elements and then returns None indefinitely.

    Useful for emulating the behavior of the built-in map() function.
    """
    return itt.chain(iterable, itt.repeat(None))

#====================================================================================================
def ncycles(iterable, n):
    '''Returns the sequence elements n times'''
    return itt.chain.from_iterable(itt.repeat(tuple(iterable), n))

#====================================================================================================
def dotproduct(vec1, vec2):
    return sum(map(operator.mul, vec1, vec2))


#====================================================================================================
def repeatfunc(func, times=None, *args):
    """Repeat calls to func with specified arguments.

    Example:  repeatfunc(random.random)
    """
    if times is None:
        return itt.starmap(func, itt.repeat(args))
    return itt.starmap(func, itt.repeat(args, times))

#====================================================================================================
def pairwise(iterable):
    '''s -> (s0,s1), (s1,s2), (s2, s3), ...'''
    a, b = itt.tee(iterable)
    next(b, None)
    return zip(a, b)

#====================================================================================================
def grouper(iterable, n, fillvalue=None):
    '''Collect data into fixed-length chunks or blocks'''
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n         #This is very clever!!  same iterator x n ==> n staggered iterators when zipping! amazing...
    return itt.zip_longest(*args, fillvalue=fillvalue)

#====================================================================================================
def chunker(it, size):
    it = iter(it)
    return iter(lambda: tuple(itt.islice(it, size)), ())

#_no_padding = object()
#def chunk(it, size, padval=_no_padding):
    #if padval == _no_padding:
        #it = iter(it)
        #sentinel = ()
    #else:
        #it = chain(iter(it), repeat(padval))
        #sentinel = (padval,) * size
    #return iter(lambda: tuple(islice(it, size)), sentinel)

#====================================================================================================
#def groupeven(*its,  n, fillvalue=None):
         #args = [iter(iterable)] * n


#====================================================================================================
def groupmore(func=None, *its):
    if not func:        func = lambda x: x
    its = sorter(*its, key=func)
    nfunc = lambda x : func(x[0])
    zipper = itt.groupby( zip(*its), nfunc )
    unzipper = ((key, zip(*groups)) for key, groups in zipper)
    return unzipper
    
#====================================================================================================
def roundrobin(*iterables):
    '''roundrobin('ABC', 'D', 'EF') --> A D E B F C'''
    # Recipe credited to George Sakkis
    pending = len(iterables)
    nexts = itt.cycle(iter(it).__next__ for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = itt.cycle(islice(nexts, pending))

#====================================================================================================
def partition(pred, iterable):
    '''Use a predicate to partition entries into false entries and true entries'''
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = itt.tee(iterable)
    return itt.filterfalse(pred, t1), filter(pred, t2)

#====================================================================================================
def teemore(*its, n=2):
    tn = itt.tee(zip(*its), n)
    return itt.starmap(zip, tn)
    
#====================================================================================================
def partitionmore(pred, *its):
    '''Partition an arbitrary number of iterables based on the truth value of a predicate evaluated 
    on the first iterator.'''
    # partition(is_odd, range(10), range) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = teemore(*its)
    return filtermorefalse(pred, *t1), filtermore(pred, *t2)
    
#====================================================================================================
def powerset(iterable):
    '''powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)'''
    s = list(iterable)
    return itt.chain.from_iterable(itt.combinations(s, r) for r in range(len(s)+1))

#====================================================================================================
def unique_everseen(iterable, key=None, **kw):
    '''List unique elements, preserving order. Remember all elements ever seen.'''
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in itt.filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element

unique = unique_everseen

#====================================================================================================
#def moreunique(*its, **kw):
    #key = kw.setdefault('key', None)
    
    
#====================================================================================================
#def unique_justseen(iterable, key=None):
    #'''List unique elements, preserving order. Remember only the element just seen.'''
    ## unique_justseen('AAAABBBCCDAABBB') --> A B C D A B
    ## unique_justseen('ABBCcAD', str.lower) --> A B C A D
    #return map(next, map(itemgetter(1), itt.groupby(iterable, key)))

#====================================================================================================
def iter_except(func, exception, first=None):
    """ Call a function repeatedly until an exception is raised.

    Converts a call-until-exception interface to an iterator interface.
    Like builtins.iter(func, sentinel) but uses an exception instead
    of a sentinel to end the loop.

    Examples:
        iter_except(functools.partial(heappop, h), IndexError)   # priority queue iterator
        iter_except(d.popitem, KeyError)                         # non-blocking dict iterator
        iter_except(d.popleft, IndexError)                       # non-blocking deque iterator
        iter_except(q.get_nowait, Queue.Empty)                   # loop over a producer Queue
        iter_except(s.pop, KeyError)                             # non-blocking set iterator

    """
    try:
        if first is not None:
            yield first()            # For database APIs needing an initial cast to db.first()
        while 1:
            yield func()
    except exception:
        pass

#====================================================================================================
def first_true(iterable, default=False, pred=None):
    """Returns the first true value in the iterable.

    If no true value is found, returns *default*

    If *pred* is not None, returns the first item
    for which pred(item) is true.

    """
    # first_true([a,b,c], x) --> a or b or c or x
    # first_true([a,b], x, f) --> a if f(a) else b if f(b) else x
    return next(filter(pred, iterable), default)

#====================================================================================================
def where_true( iterable, pred=None ):
    '''Return the indices of an iterable for which the callable pred evaluates as True'''
    func = lambda x: pred(x[1])
    return nthzip(0, *filter(func, enumerate(iterable)))

#====================================================================================================
def first_true_index(iterable, pred=None, default=None):
    '''find the first index position of the iterable for the which the callable pred returns True'''
    if pred is None:    func = lambda x : x[1]
    else:               func = lambda x : pred(x[1])
    ii = next( filter(func, enumerate(iterable)), default )     #either index-item pair or default
    return ii[0] if ii else default

def first_false_index(iterable, pred=None, default=None):
    '''find the first index position of the iterable for the which the callable pred returns False'''
    if pred is None:    func = lambda x : not x
    else:               func = lambda x : not pred(x)
    return first_true_index(iterable, func, default)

#====================================================================================================
def last_true_index(iterable, default=False, pred=None):
    return -first_true_index(reversed(iterable), pred, default)
    

#aliases
first_true_idx = first_true_index
first_false_idx = first_false_index

    
#====================================================================================================
def filtermore(func, *its):
    '''filter an arbitrary number of iterators based on the truth value of the first iterable 
    (as evaluated by function func).'''
    if func is None:    func = lambda x : x
    it00, it0 = itt.tee(its[0])         #note this consumes the iterator in position 0!!
    tf = list(map(func, it00))          #find the indices where func evaluates to true
    its = (it0,) + its[1:]              #restore the original iterator sequence
    return tuple( itt.compress(it, tf) for it in its )

#====================================================================================================
def filtermorefalse(func, *its):
    if func is None:    func = lambda x : x
    nf = lambda i: not func(i)
    return filtermore(nf, *its)