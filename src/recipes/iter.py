"""
Common patterns involving iterables.
"""

# std
import numbers
import textwrap as txw
import functools as ftl
import itertools as itt
from collections import abc, defaultdict

# third-party
import more_itertools as mit

# relative
from . import op
from .functionals import negate, on_zeroth, echo0 as echo


# ---------------------------------------------------------------------------- #
# Module constants

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
    i, (value, index) = next(itr, (0, (default, None)))
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
    test returns True
    """
    return nth_true_index(iterable, 0, test, default)


def first_false_index(iterable, test=echo, default=NULL):
    """
    Find the first index position of the iterable for the which the
    callable test returns False
    """
    return first_true_index(iterable, negate(test), default)


def last_true_index(iterable, test=bool, default=NULL):
    return -first_true_index(reversed(iterable), test, default)


# aliases
first_true_idx = first_true_index
first_false_idx = first_false_index


# ---------------------------------------------------------------------------- #
def nth_zip(n, *iters):
    """Return the nth component of the zipped sequence"""
    return tuple(mit.nth(it, n) for it in iters)


def zip_slice(start, stop, step, *iters):
    """Returns a slice of the zipped sequence of iterators"""
    return zip(*itt.islice(zip(*iters), start, stop, step))


def zip_append(items, tails):
    """Appends elements from iterator to the items in a zipped sequence."""
    return [(*zpd, app) for (zpd, app) in zip(items, tails)]


# ---------------------------------------------------------------------------- #
# Multi-indexing iterators

def where(items, *args, start=0):
    """
    Yield the indices at which items from an Iterable or Collection `items`
    evaluate `True` according to an optional test function. This function will
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

    rhs, *test = args[::-1]
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
    assert isinstance(rhs, str)   # may be tuple for op.contained etc
    assert callable(test)

    # if comparing to rhs substring with non-unit length
    if (n := len(rhs)) > 1 and (test != op.contained):
        yield from multi_index(windowed(string, n), rhs, test, start)
        return

    yield from multi_index(iter(string), rhs, test, start)
    return

# def _multi_index(string, sub):
#     start = 0
#     while start < len(string):
#         new = string.find(sub, start)
#         if new == -1:
#             break

#         yield sub, new
#         start = new + len(sub)


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

def select(items, *args, **kws):
    """
    Select truthy items from sequences. Works similar to builtin `filter`
    function, but with a more complete api.

    Three distinct call signatures are supported:

    Yield all truthy items:
    >>> select(items)               # same as `filter(None, items)`

    Yield items where `test(item)` is 
    >>> select(items, test)         # same as `filter(test, items)`

    Yield items conditionally on truth value of `test(item, value)`
    >>> select(items, test, value)  # same as `filter(lambda _: test(_, value), items)`

    In general
    >>> select(items, test, *args, **kws)
    # same as `(_ for _ in items if test(_, *args, **kws))`


    """
    if (args or kws):
        test, *args = args
        test = bool if test is None else test
        assert callable(test), f'{test} is not callable.'
        return (_ for _ in items if test(_, *args, **kws))

    return filter(None, items)
    # print valid call signatures from docstring
    # raise ValueError(txw.dedent(select.__doc__.split('\n\n', 1)[0]))


filtered = select

# ---------------------------------------------------------------------------- #
# Segmenting iterators / collections


def split(items, indices, offset=0):
    """
    Split an iterable into sub-lists at the given index positions.
    """

    if isinstance(indices, numbers.Integral):
        indices = [indices]

    if not isinstance(items, abc.Sized):
        items = list(items)

    n = len(items)
    indices = map(sum, zip(map(int, indices), itt.repeat(int(offset))))
    if indices := sorted(map(n.__rmod__, indices)):  # resolve negatives
        for i, j in mit.pairwise([0, *indices, n]):
            yield items[i:j]
    else:
        yield items


def split_where(items, *args, start=0, offset=0):
    """
    Split a list into sublists at the positions of positive test evaluation.
    """
    return split(items, where(items, *args, start=start), offset)


def split_like(items, like):
    """
    Split a container `items` into -containers, each with the same size as the
    sequence of (differently sized) containers in `like`.
    """

    *indices, total = itt.accumulate(map(len, like))
    assert len(items) == total
    return split(items, indices)


def split_non_consecutive(items, step=1):
    return split(items, where(diff(items), op.ne, 1), 1)


def diff(items):
    if len(items) <= 1:
        return

    yield from map(op.rsub, *zip(*mit.pairwise(items)))


def split_slices(indices):
    """
    Generate slices for splitting a collection at index positions `indices`.
    """
    return map(slice, *zip(*mit.pairwise(itt.chain([0], indices))))


def chunker(itr, size):
    return iter(map(tuple, itt.islice(iter(itr), size)), ())


def windowed(obj, size, step=1):
    assert isinstance(size, numbers.Integral)

    if isinstance(obj, str):
        for i in range(0, len(obj), step):
            yield obj[i:i + size]
        return

    yield from mit.windowed(obj, size)


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


def _parse_predicate(func_or_iter, iters):

    if isinstance(func_or_iter, abc.Iterable):
        # handle eg: cofilter([...])
        return bool, (func_or_iter, *iters)

    if callable(func_or_iter) or (func_or_iter is None):
        return (func_or_iter or bool), iters

    raise TypeError(
        f'Predicate function should be a callable object (or `None`), not '
        f'an instance of {type(func_or_iter)}.'
    )


def cofilter(func_or_iter, *iters):
    """
    Filter an arbitrary number of iterables based on the truth value of the
    first iterable. An optional predicate function that determines the truth
    value of elements can be passed as the first argument, followed by the
    iterables.

    cofilter(None, ...) is equivalent to
    cofilter(bool, ...)
    """
    func, iters = _parse_predicate(func_or_iter, iters)

    if not iters:
        return iters

    # zip(*filter(lambda x: func(x[0]), zip(*iters)))
    # clone the iterable in position 0, since we consume it below for evaluation
    first, clone = itt.tee(iters[0])
    # for first iterable, find the indices where func(element) evaluates to True
    tf = list(map(func, clone))
    # restore the original iterable sequence, select truthy items
    return tuple(itt.compress(it, tf) for it in (first, *iters[1:]))


def copartition(pred, *iters):
    """
    Partition an arbitrary number of iterables based on the truth value of a
    predicate evaluated on the first iterator.

    partition(is_odd, range(10), range) --> (1 3 5 7 9), (0 2 4 6 8)
    """
    t1, t2 = cotee(*iters)
    return cofilter(pred, *t2), cofilter(negate(pred), *t1)


def cogroup(func=echo, *iters, unzip=True, **kws):
    # avoid circular import
    from recipes.containers import cosort

    iters = cosort(*iters, key=func)
    zipper = itt.groupby(zip(*iters), on_zeroth(func))
    return ((key, zip(*groups)) for key, groups in zipper) if unzip else zipper


def cosplit(*iters, indices, offset=0):
    for items in split(zip(*iters), indices, offset):
        yield tuple(zip(*items))


def cotee(*iters, n=2):
    tn = itt.tee(zip(*iters), n)
    return itt.starmap(zip, tn)


# ---------------------------------------------------------------------------- #
# Duplicate detection / filtering

def unique(items, consecutive=False):
    """
    Return tuples of unique (item, indices) pairs for sequence `items`.
    """

    buffer = defaultdict(list)
    for i, item in enumerate(items):
        if (previous := buffer[item]) and (i != previous[-1] + 1) and consecutive:
            yield from buffer.items()
            buffer = defaultdict(list)

        buffer[item].append(i)
    #
    yield from buffer.items()


def duplicates(items, consecutive=False):
    """Yield tuples of item, indices pairs for duplicate values."""
    for key, indices in unique(items, consecutive):
        if (len(indices) > 1):
            yield key, indices


def where_duplicate(items, consecutive=False):
    """Indices of duplicate entries"""
    for _, indices in duplicates(items, consecutive):
        yield indices


def unduplicate(items, test):
    """Filter duplicate items based on condition `test`."""

    results = set()
    for item in items:
        result = test(item)
        if result not in results:
            yield item

        results.add(result)


def non_unique(itr):
    prev = next(itr, NULL)
    if prev is NULL:
        return

    for item in itr:
        if item == prev:
            yield prev
        prev = item


# aliases
where_duplicates = where_duplicate
filter_duplicates = filter_duplicate = deduplicate = unduplicate


# ---------------------------------------------------------------------------- #

def flip_lr(data):
    return map(reversed, data)


def flip_ud(data):
    return flip_lr(zip(*data))
