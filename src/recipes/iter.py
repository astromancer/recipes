"""
Common patterns involving iterables.
"""


# std
import numbers
import textwrap as txw
import functools as ftl
import itertools as itt
from collections import abc

# third-party
import more_itertools as mit

# relative
from . import op
from .functionals import negate, on_zeroth, echo0 as echo


# ---------------------------------------------------------------------------- #
#
NULL = object()
#
INDEX_MAX = int(1e8)


# ---------------------------------- helpers --------------------------------- #

def as_iter(obj, exclude=(str,), return_as=list):
    """
    Converts the input object to an iterable.
    exclude     : objects that will not be considered iterables.
    return_as   : specified type to convert the object to
    """
    if exclude is None:
        exclude = ()

    if isinstance(obj, exclude) or not isinstance(obj, abc.Iterable):
        return return_as([obj])
    return obj


# alias
as_sequence = as_iter
# as_sequence_unless_str


# ---------------------------------------------------------------------------- #
# Indexing helpers

def nth_true(iterable, n, test=echo, default=NULL, return_index=True):
    index, value = _nth_true(iterable, n, test, default)
    return (index, value) if return_index else value


def _nth_true(iterable, n, test=echo, default=NULL):
    """
    Find the `n`th index position of the `iterable` for the which the callable
    `test` returns True. If no such element exists, return `default` value.
    """
    assert isinstance(n, numbers.Integral) and n >= 0

    # itr = itt.chain(filter(test, iterable), itt.repeat(default))
    # mit.nth(it, n, default)

    filtered, index = cofilter(test, iterable, itt.count())
    itr = enumerate(zip(filtered, index))
    mit.consume(itr, n)
    i, (value, index) = next(itr, default)
    if value is NULL:
        if i < n:
            raise ValueError(
                f'Iterable contains only {i} (< {n}) truthy elements (based on '
                f'test function {test}). You may supply any default value to '
                'suppress this error.'
            )

    return index, value


def nth_true_index(iterable, n, test=echo, default=NULL):
    return _nth_true(iterable, n, test, default)[0]


def first_true_index(iterable, test=echo, default=NULL):
    """
    Find the first index position of the iterable for the which the callable
    pred returns True
    """
    return nth_true_index(iterable, 0, test, default)


def first_false_index(iterable, test=echo, default=NULL):
    """
    Find the first index position of the iterable for the which the
    callable pred returns False
    """
    return first_true_index(iterable, negate(test), default)


def last_true_index(iterable, test=bool, default=NULL):
    return -first_true_index(reversed(iterable), test, default)


# aliases
first_true_idx = first_true_index
first_false_idx = first_false_index


# ---------------------------------------------------------------------------- #
def nth_zip(n, *its):
    """Return the nth component of the zipped sequence"""
    return tuple(mit.nth(it, n) for it in its)


def zip_slice(start, stop, step, *its):
    """Returns a slice of the zipped sequence of iterators"""
    return zip(*itt.islice(zip(*its), start, stop, step))


def zip_append(items, tails):
    """Appends elements from iterator to the items in a zipped sequence."""
    return [(*zpd, app) for (zpd, app) in zip(items, tails)]


# ---------------------------------------------------------------------------- #
# Multi-indexing iterators


def where(items, *args, start=0):
    """
    Yield the indices at which items from an Iterable or Collection `items`
    evaluate True according to an optional test function. This function will
    consume the iterable, so take care not to pass infinite iterables - the
    function will raise an exception if the iteration count is greater than the
    value of the module constant `INDEX_MAX` (by default 10**8).

    Three distinct call signatures are supported:
        >>> where(items)                # yield indices where items are truthy
        >>> where(items, value)         # yield indices where items equal value
        >>> where(items, func, value)   # conditionally on func(item, value)

    Parameters
    ----------
    items : Iterable
        Any iterable. Note that this function will consume the iterable.
    args : ([test], rhs)
        test : callable, optional
            Function for testing, should return bool, by default op.eq.
        rhs : object
            Right hand side item for equality test.
    start : int, optional
        Starting index for search, by default 0.

    Yields
    ------
    int
        Index at which `item` was found or `test` evaluated True

    Raises
    ------
    ValueError
        On receiving invalid number of function arguments.
    """
    assert isinstance(start, numbers.Integral)

    nargs = len(args)
    if nargs == 0:
        _, indices = cofilter(items, itt.count(start))
        return indices

    if nargs > 2:
        # print valid call signatures from docstring
        raise ValueError(txw.dedent(where.__doc__.split('\n\n')[1]))

    *test, rhs = args
    test, = test or [op.eq]

    yield from multi_index(items, rhs, test, start)


# ---------------------------------------------------------------------------- #
# Dispatch for multi-indexing


@ftl.singledispatch
def multi_index(obj, rhs, test=bool, start=0):
    """default dispatch for multi-indexing"""
    raise TypeError(f'Object of type {type(obj)} is not an iterable.')


@multi_index.register(str)
def _(string, rhs, test=op.eq, start=0):
    # ensure we are comparing to str
    assert isinstance(rhs, str)
    assert callable(test)

    # if comparing to rhs substring with non-unit length
    if (n := len(rhs)) > 1 and (test != op.contained):
        yield from multi_index(windowed(string, n), rhs, test, start)
        return

    yield from multi_index(iter(string), rhs, test, start)
    return


@multi_index.register(dict)
def _(obj, rhs, test=op.eq, start=None):
    if start:
        raise NotImplementedError

    # cofilter
    yield from (k for k, o in obj.items() if test(o, rhs))


@multi_index.register(abc.Iterable)
def _(obj, rhs, test=op.eq, start=0):

    if start:
        mit.consume(obj, start)

    indices = (i for i, x in enumerate(obj, start) if test(x, rhs))
    sentinel = itt.chain(itt.repeat(False, INDEX_MAX - 1), [True])
    for i in indices:
        if next(sentinel):
            raise RuntimeError(
                'Infinite iterable? If this is wrong, increase the `INDEX_MAX`.'
                ' eg: \n'
                '>>> import recipes.iter as itr\n'
                '... itr.INDEX_MAX = 1e9')
        yield i


# ---------------------------------------------------------------------------- #
# Filtering / element selection
def select(items, *args, start=0):
    """

    Three distinct call signatures are supported:
    >>> select(items)               # yield `items` that are truthy
    >>> select(items, test)         # yield items where `test(item)` is truthy
    >>> select(items, test, value)  # yield conditionally on `test(item, value)`


    Parameters
    ----------
    items : _type_
        _description_
    start : int, optional
        _description_, by default 0

    Examples
    --------
    >>> 

    Returns
    -------
    _type_
        _description_

    Raises
    ------
    ValueError
        _description_
    """

    assert isinstance(start, numbers.Integral)

    nargs = len(args)
    if nargs == 0:
        return filter(None, items)

    if nargs == 1:
        test, = args
        assert callable(test)
        return filter(negate(test), items)

    if nargs == 2:
        test, rhs = args
        return (_ for _ in items if test(_, rhs))

    # print valid call signatures from docstring
    raise ValueError(txw.dedent(select.__doc__.split('\n\n')[1]))


# ---------------------------------------------------------------------------- #
# slicing
def windowed(obj, size, step=1):
    assert isinstance(size, numbers.Integral)

    if isinstance(obj, str):
        for i in range(0, len(obj), step):
            yield obj[i:i + size]
        return

    yield from mit.windowed(obj, size)


# ---------------------------------------------------------------------------- #
# Segmenting iterators / collections

def split(l, idx):
    """Split a list into sub-lists at the given indices"""

    if isinstance(idx, numbers.Integral):
        idx = [idx]

    if idx := sorted(idx):
        for i, j in mit.pairwise([0, *idx, len(l)]):
            yield l[i:j]
    else:
        yield l


# def split(l, idx):
#     if isinstance(idx, numbers.Integral):
#         idx = [idx]

#     idx = iter(sorted(idx))

#     i, j = 0, None
#     for j in idx:
#         yield l[i:j]
#         i = j

#     if j is not None:
#         yield l[j:]

def split_slices(indices):
    """
    Generate slices for splitting a collection at index positions `indices`.
    """
    return map(slice, *zip(*mit.pairwise(itt.chain([0], indices))))


def chunker(itr, size):
    return iter(map(tuple, itt.islice(iter(itr), size)), ())


# ---------------------------------------------------------------------------- #
# Cyclic iterators

def cyclic(obj, n=None):
    """
    Cyclic iterator. Will cycle (optionally only up to `n` items). If ``obj``
    is not iterable, it will be repeated `n` times.
    """
    cyc = itt.cycle(mit.always_iterable(obj))
    return itt.islice(cyc, n)


def iter_repeat_last(it):
    """
    Yield items from the input iterable and repeat the last item indefinitely
    """
    it, it1 = itt.tee(mit.always_iterable(it))
    return mit.padded(it, next(mit.tail(1, it1)))


# ---------------------------------------------------------------------------- #
# Simultaneous (co) operations on multiple iterables

def cogroup(func=echo, *its, unzip=True, **kws):
    # avoid circular import
    from recipes.lists import cosort

    its = cosort(*its, key=func)
    zipper = itt.groupby(zip(*its), on_zeroth(func))
    return ((key, zip(*groups)) for key, groups in zipper) if unzip else zipper


def cotee(*its, n=2):
    tn = itt.tee(zip(*its), n)
    return itt.starmap(zip, tn)


def copartition(pred, *its):
    """
    Partition an arbitrary number of iterables based on the truth value of a
    predicate evaluated on the first iterator.

    partition(is_odd, range(10), range) --> (1 3 5 7 9), (0 2 4 6 8)
    """
    t1, t2 = cotee(*its)
    return cofilter(pred, *t2), cofilter(negate(pred), *t1)


def cofilter(func_or_iter, *its):
    """
    Filter an arbitrary number of iterators based on the truth value of the
    first iterable. An optional predicate function that determines the truth
    value of elements can be passed as the first argument, followed by the
    iterables.
    """
    its, func = _parse_iterable_filter(func_or_iter, its)

    # zip(*filter(lambda x: func(x[0]), zip(*its)))

    it00, it0 = itt.tee(its[0])
    # NOTE this consumes the iterator in position 0!!
    # find the indices where func evaluates to true
    tf = list(map(func, it00))
    # restore the original iterator sequence
    its = (it0, *its[1:])
    return tuple(itt.compress(it, tf) for it in its)


def _parse_iterable_filter(func_or_iter, its):
    if (func_or_iter is None) or isinstance(func_or_iter, abc.Iterable):
        # handle cofilter(None, ...) // cofilter((1, None), (2, 4))
        func = bool
        its = (func_or_iter, *its)
    elif callable(func_or_iter):
        func = func_or_iter
    else:
        raise TypeError(f'Predicate function should be a callable object (or '
                        f'`None`), not an instance of {type(func)}.')

    return its, func


# ---------------------------------------------------------------------------- #
# Duplicate detection / filtering

def duplicates(l):
    """Yield tuples of item, indices pairs for duplicate values."""
    from recipes.lists import unique

    for key, idx in unique(l).items():
        if len(idx) > 1:
            yield key, idx


def filter_duplicates(l, test):
    """Filter duplicate items based on condition `test`."""
    results = set()
    for item in l:
        result = test(item)
        if result not in results:
            yield item

        results.add(result)


# aliases
unduplicate = filter_duplicates


def non_unique(itr):
    prev = next(itr, NULL)
    if prev is NULL:
        return

    for item in itr:
        if item == prev:
            yield prev
        prev = item


# ---------------------------------------------------------------------------- #
# Super / subclass iterators

def subclasses(cls, _seen=None):
    """
    Generator over all subclasses of a given class, in depth first order.

    >>> list(iter_subclasses(int)) == [bool]
    True

    >>> class A: pass
    >>> class B(A): pass
    >>> class C(A): pass
    >>> class D(B,C): pass
    >>> class E(D): pass
    >>> list(iter_subclasses(A))
    [__main__.B, __main__.D, __main__.E, __main__.C]

    >>> # get ALL (new-style) classes currently defined
    >>> [cls.__name__ for cls in iter_subclasses] #doctest: +ELLIPSIS
    ['type', ... 'tuple', ...]
    """

    # recipe adapted from:
    # http://code.activestate.com/recipes/576949-find-all-subclasses-of-a-given-class/

    if not isinstance(cls, type):
        from recipes.oo.repr_helpers import qualname
        raise TypeError(f'{qualname(subclasses)}` must be called with new-style'
                        f' classes, not {cls!r}.')

    _seen = _seen or set()
    for sub in cls.__subclasses__(*([cls] if (cls is type) else ())):
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            yield from subclasses(sub, _seen)


def superclasses(cls, _seen=None):

    if not isinstance(cls, type):
        raise TypeError('`iter.baseclasses` must be called with new-style '
                        'classes, not {cls!r}.')

    _seen = _seen or set()

    chain = []
    for base in cls.__bases__:
        if base not in _seen:
            _seen.add(base)
            yield base
            chain.append(superclasses(base, _seen))

    yield from itt.chain(*chain)


# alias
baseclasses = superclasses
