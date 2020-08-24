"""
Common patterns involving iterables
"""


# std libs
import operator
import functools
import itertools as itt
from collections import abc

# third-party libs
import more_itertools as mit


# ---------------------------------- helpers --------------------------------- #
def _echo(x):
    return x


def not_none(x):
    return x is not None


# -------------------------------- decorators -------------------------------- #
def negate(func):
    def wrapped(obj):
        return not func(obj)
    return wrapped


def on_nth(func, n):
    def wrapped(obj):
        return func(obj[n])


def on_zeroth(func):
    return on_nth(func, 0)


def on_first(func):
    return on_nth(func, 1)

# ---------------------------------------------------------------------------- #
def non_unique(itr):
    prev = next(itr)
    for item in itr:
        if item == prev:
            yield prev
        prev = item


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
    else:
        return obj


# alias
as_sequence = as_iter
# as_sequence_unless_str


def split(l, idx):
    """Split a list into sub-lists at the given indices"""
    return map(l.__getitem__, itt.starmap(slice, mit.pairwise(idx)))


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


def chunker(itr, size):
    return iter(map(tuple, itt.islice(iter(itr), size)), ())


def group_more(func=_echo, *its, **kws):
    # avoid circular import
    from recipes.containers.lists import cosort

    its = cosort(*its, key=func)
    zipper = itt.groupby(zip(*its), on_zeroth(func))
    if kws.get('unzip', True):
        unzipper = ((key, zip(*groups)) for key, groups in zipper)
        return unzipper
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
    return cofilter(pred, *t2), cofilter_false(pred, *t1)


def where(iterable, pred=bool):
    """
    Return the indices of an iterable for which the callable ``pred'' evaluates
    as True
    """
    return nth_zip(0, *filter(on_first(pred), enumerate(iterable)))


def where_false(iterable, pred=bool):
    return where(iterable, negate(pred))


def first(iterable, pred=bool, default=None):
    return next(filter(pred, iterable), default)


def first_true_index(iterable, pred=_echo, default=None):
    """
    Find the first index position of the iterable for the which the callable
    pred returns True
    """

    index, _ = first(enumerate(iterable), on_first(pred), (None, None))
    return index or default


def first_false_index(iterable, pred=_echo, default=None):
    """
    Find the first index position of the iterable for the which the
    callable pred returns False
    """
    return first_true_index(iterable, negate(pred), default)


def last_true_index(iterable, pred=bool, default=False):
    return -first_true_index(reversed(iterable), pred, default)


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


def cofilter_false(func, *its):
    return cofilter(negate(func or bool), *its)


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
