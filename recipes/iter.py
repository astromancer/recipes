"""
Common patterns involving iterables
"""


# std libs
import operator
import functools
import itertools as itt
from collections import Iterable

# third-party libs
import more_itertools as mit



# TODO: Wrapper class which Implements a .list method


def as_iter(obj, exclude=(str,), return_as=list):
    """
    Converts the input object to an iterable.
    exclude     : objects that will not be considered iterables.
    return_as   : specified type to convert the object to
    """
    if exclude is None:
        exclude = ()

    if isinstance(obj, exclude) or not isinstance(obj, Iterable):
        return return_as([obj])
    else:
        return obj


# alias
as_sequence = as_iter
# as_sequence_unless_str


def flatiter(items):
    """generator that flattens an iterator with arbitrary nesting"""
    for item in items:
        # catches the infinite recurence resulting from character-string duality
        if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            for i in flatiter(item):
                yield i
        else:
            yield item


# alias
flatten = flatiter


# def flatiter(items):
#     """generator that flattens an iterator with arbitrary nesting"""
#     for item in items:
#         #catches the infinite recurence resulting from character-string duality
#         if isinstance(item, (str, bytes)):
#             yield item
#         else:
#             try:
#                 for i in flatiter(item):
#                     yield i
#             except TypeError as err:
#                 tb = traceback.format_exc()
#                 # avoid obscuring legitimate TypeErrors by checking specifically or
#                 if tb.endswith('object is not iterable\n'):
#                     yield item
#                 raise err


# def flatiter(*items):          #raises RecursionError
# """generator that flattens an iterator with arbitrary nesting"""
# for item in items:
##catches the infinite recurence resulting from character-string duality
# if isinstance(item, (str, bytes)):
# yield item
# else:
# try:
# for i in flatiter(item):
# yield i
# except TypeError:
# yield item

# def flatiter(*items, maxdepth=None):
# """
# Generator that flattens an iterator with arbitrary nesting.
# Optionally provide maximum depth to flatten to.
# """
# if maxdepth is None:
# yield from _flatiter(items)
# else:
# def _flatit(item, depth):
# if depth >= maxdepth:
# yield item
# elif isinstance(item, (str, bytes)):
# yield item
# else:
# yield from _flatit(l, depth+1)

# yield from _flatit(l, 0)


def interleave(*its, **kw):
    """interleaves two Iterables."""
    return_as = kw.get('return_as', list)
    if 'fill' in kw:
        zipper = functools.partial(itt.zip_longest, fillvalue=kw['fill'])
    else:
        zipper = zip
    return return_as([val for items in zipper(*its) for val in items])


def iter_split(L, idx):
    """Split a list into sub-lists at the given indices"""
    return map(L.__getitem__, itt.starmap(slice, mit.pairwise(idx)))


def cyclic(obj, n=None):
    """
    Cyclic iterator. Will cycle (optionally only up to `n` items).  If ``obj``
    is not iterable, it will be repeated `n` times.
    """
    cyc = itt.cycle(mit.always_iterable(obj))
    return itt.islice(cyc, n)


#
# def n_cycles(iterable, n):
#     """Returns the sequence elements n times"""
#     return itt.chain.from_iterable(itt.repeat(tuple(iterable), n))


def nth_zip(n, *its):
    """Return the nth component of the zipped sequence"""
    return tuple(mit.nth(it, n) for it in its)


def zip_slice(start, stop, step, *its):
    """Returns a slice of the zipped sequence of iterators"""
    return zip(*itt.islice(zip(*its), start, stop, step))


def zip_app(zipped, apper):
    """Appends elements from iterator to the items in a zipped sequence."""
    return [zpd + (app,) for (zpd, app) in zip(zipped, apper)]


def pad_none(iterable):
    """Returns the sequence elements and then returns None indefinitely.

    Useful for emulating the behavior of the built-in map() function.
    """
    return itt.chain(iterable, itt.repeat(None))


def dot_product(vec1, vec2):
    return sum(map(operator.mul, vec1, vec2))


def chunker(it, size):
    it = iter(it)
    return iter(lambda: tuple(itt.islice(it, size)), ())


# def ichunker(it, size):
# it = iter(it)
# return iter(lambda: itt.islice(it, size), ())

# _no_padding = object()
# def chunk(it, size, padval=_no_padding):
# if padval == _no_padding:
# it = iter(it)
# sentinel = ()
# else:
# it = chain(iter(it), repeat(padval))
# sentinel = (padval,) * size
# return iter(lambda: tuple(islice(it, size)), sentinel)


# def groupeven(*its,  n, fillvalue=None):
# args = [iter(iterable)] * n


def group_more(func=None, *its, **kws):
    from recipes.list import sorter
    if not func:
        func = lambda x: x
    its = sorter(*its, key=func)
    nfunc = lambda x: func(x[0])
    zipper = itt.groupby(zip(*its), nfunc)
    if kws.get('unzip', True):
        unzipper = ((key, zip(*groups)) for key, groups in zipper)
        return unzipper
    return zipper


def tee_more(*its, n=2):
    tn = itt.tee(zip(*its), n)
    return itt.starmap(zip, tn)


def partition_more(pred, *its):
    """
    Partition an arbitrary number of iterables based on the truth value of a
    predicate evaluated on the first iterator.

    partition(is_odd, range(10), range) --> (1 3 5 7 9), (0 2 4 6 8)
    """
    t1, t2 = tee_more(*its)
    return filter_more(pred, *t2), filter_more_false(pred, *t1)


def where_true(iterable, pred=bool):
    """
    Return the indices of an iterable for which the callable ``pred'' evaluates
    as True
    """
    func = lambda x: pred(x[1])
    return nth_zip(0, *filter(func, enumerate(iterable)))


def where_false(iterable, pred=bool):
    func = lambda x: not pred(x)
    return where_true(iterable, func)


def first_true_index(iterable, pred=None, default=None):
    """
    Find the first index position of the iterable for the which the callable
    pred returns True.
    """
    if pred is None:
        func = lambda x: x[1]
    else:
        func = lambda x: pred(x[1])
    ii = next(filter(func, enumerate(iterable)), default)
    # ii - either index-item pair or default
    return ii[0] if ii else default


def first_false_index(iterable, pred=None, default=None):
    """
    Find the first index position of the iterable for the which the
    callable pred returns False
    """
    if pred is None:
        func = lambda x: not x
    else:
        func = lambda x: not pred(x)
    return first_true_index(iterable, func, default)


def last_true_index(iterable, default=False, pred=None):
    return -first_true_index(reversed(iterable), pred, default)


# aliases
first_true_idx = first_true_index
first_false_idx = first_false_index


def filter_more(func, *its):
    """
    Filter an arbitrary number of iterators based on the truth value of the
    first iterable (as evaluated by function func).
    """
    if func is None:
        func = lambda x: x
    it00, it0 = itt.tee(
            its[0])  # note this consumes the iterator in position 0!!
    tf = list(map(func, it00))  # find the indices where func evaluates to true
    its = (it0,) + its[1:]  # restore the original iterator sequence
    return tuple(itt.compress(it, tf) for it in its)


def filter_more_false(func, *its):
    if func is None:
        func = lambda x: x
    nf = lambda i: not func(i)
    return filter_more(nf, *its)


def itersubclasses(cls, _seen=None):
    # recipe from http://code.activestate.com/recipes/576949-find-all-subclasses-of-a-given-class/
    """
    itersubclasses(cls)

    Generator over all subclasses of a given class, in depth first order.

    >>> list(itersubclasses(int)) == [bool]
    True
    >>> class A(object): pass
    >>> class B(A): pass
    >>> class C(A): pass
    >>> class D(B,C): pass
    >>> class E(D): pass
    >>>
    >>> for cls in itersubclasses(A):
    ...     print(cls.__name__)
    B
    D
    E
    C
    >>> # get ALL (new-style) classes currently defined
    >>> [cls.__name__ for cls in itersubclasses(object)] #doctest: +ELLIPSIS
    ['type', ...'tuple', ...]
    """

    if not isinstance(cls, type):
        raise TypeError('itersubclasses must be called with '
                        'new-style classes, not %.100r' % cls)
    if _seen is None:
        _seen = set()
    try:
        subs = cls.__subclasses__()
    except TypeError:  # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, _seen):
                yield sub
