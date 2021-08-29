"""
Common patterns involving iterables.
"""


# std
import numbers
import itertools as itt
from collections import abc

# third-party
import more_itertools as mit

# relative
from . import op
from .functionals import negate, echo0 as echo


# ---------------------------------- helpers --------------------------------- #
class null:
    pass


def not_none(x):
    return x is not None


# -------------------------------- decorators -------------------------------- #

def on_nth(func, n):
    def wrapped(obj):
        return func(obj[n])
    return wrapped


def on_zeroth(func):
    return on_nth(func, 0)


def on_first(func):
    return on_nth(func, 1)

# ---------------------------------------------------------------------------- #


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


# def where(iterable, test=bool):
#     return nth_zip(0, *filter(on_first(test), enumerate(iterable)))

def where(l, item, start=0, test=op.eq):
    """
    Yield the indices at which the callable ``test'' evaluates True
    """
    i = start
    n = len(l)
    while i < n:
        try:
            # pylint: disable=too-many-function-args
            i = op.index(l, item, i, test)
            yield i
        except ValueError:
            # done
            return
        else:
            i += 1  # start next search one on


def split(l, idx):
    """Split a list into sub-lists at the given indices"""

    if isinstance(idx, numbers.Integral):
        idx = [idx]

    idx = sorted(idx)
    if idx:
        idx = [0, *idx, len(l)]
        for i, j in mit.pairwise(idx):
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


def non_unique(itr):
    prev = next(itr, null)
    if prev is null:
        return

    for item in itr:
        if item == prev:
            yield prev
        prev = item


def cyclic(obj, n=None):
    """
    Cyclic iterator. Will cycle (optionally only up to `n` items).  If ``obj``
    is not iterable, it will be repeated `n` times.
    """
    cyc = itt.cycle(mit.always_iterable(obj))
    return itt.islice(cyc, n)


def nth_zip(n, *its):
    """Return the nth component of the zipped sequence"""
    return tuple(mit.nth(it, n) for it in its)


def zip_slice(start, stop, step, *its):
    """Returns a slice of the zipped sequence of iterators"""
    return zip(*itt.islice(zip(*its), start, stop, step))


def zip_append(items, tails):
    """Appends elements from iterator to the items in a zipped sequence."""
    return [(*zpd, app) for (zpd, app) in zip(items, tails)]


def pad_none(iterable):
    """
    Returns the sequence elements and then returns None indefinitely.

    Useful for emulating the behavior of the built-in map() function.
    """
    return itt.chain(iterable, itt.repeat(None))


def chunker(itr, size):
    return iter(map(tuple, itt.islice(iter(itr), size)), ())


def group_more(func=echo, *its, unzip=True, **kws):
    # avoid circular import
    from recipes.lists import cosort

    its = cosort(*its, key=func)
    zipper = itt.groupby(zip(*its), on_zeroth(func))
    if unzip:
        return ((key, zip(*groups)) for key, groups in zipper)
    return zipper


def tee_more(*its, n=2):
    tn = itt.tee(zip(*its), n)
    return itt.starmap(zip, tn)


def copartition(pred, *its):
    """
    Partition an arbitrary number of iterables based on the truth value of a
    predicate evaluated on the first iterator.

    partition(is_odd, range(10), range) --> (1 3 5 7 9), (0 2 4 6 8)
    """
    t1, t2 = tee_more(*its)
    return cofilter(pred, *t2), cofilter(negate(pred), *t1)


# def first(iterable, pred=bool, default=None):
#     return next(filter(pred, iterable), default)


def first_true_index(iterable, test=echo, default=None):
    """
    Find the first index position of the iterable for the which the callable
    pred returns True
    """

    index, _ = mit.first_true(enumerate(iterable), (None, None), on_first(test))
    if index is None:
        return default
    return index


def first_false_index(iterable, test=echo, default=None):
    """
    Find the first index position of the iterable for the which the
    callable pred returns False
    """
    return first_true_index(iterable, negate(test), default)


def last_true_index(iterable, test=bool, default=False):
    return -first_true_index(reversed(iterable), test, default)


# aliases
first_true_idx = first_true_index
first_false_idx = first_false_index


def cofilter(func, *its):
    """
    Filter an arbitrary number of iterators based on the truth value of the
    first iterable (as evaluated by function func).
    """
    func = func or bool
    it00, it0 = itt.tee(its[0])
    # note this consumes the iterator in position 0!!
    # find the indices where func evaluates to true
    tf = list(map(func, it00))
    # restore the original iterator sequence
    its = (it0,) + its[1:]
    return tuple(itt.compress(it, tf) for it in its)


# def cofilter_false(func, *its):
#     return cofilter(negate(func or bool), *its)


def duplicates(l):
    """Yield tuples of item, indices pairs for duplicate values."""
    from recipes.lists import unique

    for key, idx in unique(l).items():
        if len(idx) > 1:
            yield key, idx


def iter_repeat_last(it):
    """
    Yield items from the input iterable and repeat the last item indefinitely
    """
    it, it1 = itt.tee(mit.always_iterable(it))
    return mit.padded(it, next(mit.tail(1, it1)))
