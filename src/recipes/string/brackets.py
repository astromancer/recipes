"""
Tools for parsing and editing strings containing (nested) brackets.
"""

# std
import operator as op
from collections import defaultdict
from dataclasses import asdict, astuple, dataclass
from typing import Callable, Collection, List, Tuple, Union

# local
# import docsplice as doc

# relative
from .. import op
from ..functionals import always
from ..iter import cofilter, where
from . import delete


# Braces(string) # TODO / .tokenize / .parse
# # __all__ = ['BracketParser', 'braces', 'square', 'round', 'chevrons']

ALL_BRACKET_PAIRS = ('()', '[]', '{}', '<>')
PAIRED = dict(ALL_BRACKET_PAIRS)
PAIRED.update(dict(zip(PAIRED.values(), PAIRED.keys())))


SYMBOLS = {op.eq: '==',
           op.lt: '<',
           op.le: '≤',
           op.gt: '>',
           op.ge: '≥'}

# ---------------------------------------------------------------------------- #
# function that always returns True
always_true = always(True)


class is_outer:
    """
    Conditional to check if brackets are outermost enclosing pair.
    """

    def __init__(self, string):
        self.n = len(string)

    def __call__(self, match):
        return ((match.start == match.level) and
                (match.end == self.n - match.level - 1))


# ---------------------------------------------------------------------------- #


@dataclass
class Condition:
    """
    Collection of conditional tests on BracketPair attributes. Used for 
    filtering BracketPair from iterable.

    """
    enclosed:   Union[Callable, str] = always_true
    indices:    Union[Callable, Collection[int]] = always_true
    level:      Union[Callable, int] = always_true
    brackets:   Union[Callable, Collection[str], str] = always_true

    def __post_init__(self):
        for key, val in asdict(self).items():
            if not callable(val):
                setattr(self, key, val.__eq__)

    def __call__(self, match):
        return (self.enclosed(match.enclosed) and
                self.indices(match.indices) and
                self.level(match.level) and
                self.brackets(match.brackets))


# ---------------------------------------------------------------------------- #


class Comparison:
    """
    A function factory that wraps the comparison operators for future
    excecution.
    """

    def __init__(self, name, op):
        self.name = name
        self.op = op

    def __call__(self, rhs):
        """
        Create `Compare` object for delayed comparison.
        """
        return Compare(self.name, self.op, rhs)


class Compare:
    """Comparison operator wrapper for comparing variable lhs with fixed rhs"""

    def __init__(self, name, op_, rhs):
        self.name = name
        self.op = op_
        self.rhs = rhs

    def __call__(self, lhs):
        return self.op(lhs, self.rhs)

    def __str__(self):
        return f'({self.name}{SYMBOLS[self.op]}{self.rhs})'

    __repr__ = __str__

    def __logic(self, op_, rhs):
        if isinstance(rhs, ChainedCompare):
            rhs.args.append(self)
            rhs.ops.append(op_)
            return rhs

        if isinstance(rhs, Compare):
            return ChainedCompare((self, rhs), (op_,))

        raise TypeError(f'Invalid type {type(rhs)} encountered on right hand '
                        f'side while constructing `ChainedComparison` object.')

    def __or__(self, rhs):
        return self.__logic(op.or_, rhs)

    def __and__(self, rhs):
        return self.__logic(op.and_, rhs)


class ChainedCompare:
    def __init__(self, comps, ops):
        self.comps = comps
        self.ops = ops

    def __call__(self, obj):
        # reduce
        init, *comps = self.comps
        result = init(getattr(obj, init.name))
        for op_, cmp in zip(self.ops, comps):
            result = op_(result, cmp(getattr(obj, cmp.name)))
        return result


def lazy(name):
    class FutureComparisonAbstract:
        """Abstraction layer for delayed evaluation of comparison operators."""
        __eq__ = Comparison(name, op.eq)
        __lt__ = Comparison(name, op.lt)
        __le__ = Comparison(name, op.le)
        __gt__ = Comparison(name, op.gt)
        __ge__ = Comparison(name, op.ge)

    return FutureComparisonAbstract()


# condition testing helpers
brackets = lazy('brackets')
string = lazy('string')
indices = lazy('indices')
level = lazy('level')


# ---------------------------------------------------------------------------- #
@dataclass
class BracketPair:
    """
    Object representing a pair of brackets at some position and nesting level in
    a string.
    """

    brackets: Tuple[str]
    """Characters or strings for opening and closing bracket. Must have length
        of 2."""
    enclosed: str
    indices: List[int] = (None, None)
    """Indices of opening- and closing bracket pairs."""
    level: int = 0

    def __post_init__(self):
        self.open, self.close = self.brackets
        self.start, self.end = self.indices

    def __iter__(self):
        yield from astuple(self)[1:]

    def __str__(self):
        return self.enclosed  # or ''

    def __bool__(self):
        return any((self.enclosed, *self.indices))

    # @ftl.cached_property
    @property
    def full(self):
        return self.enclosed.join(self.brackets)


def get_test(condition, string):
    """
    Function wrapper to support multiple call signatures for user defined
    condition tests.
    """
    if not callable(condition):
        raise TypeError(
            'Parameter `condition` should be a callable, or '
            f'preferably a `Condition` object, not {type(condition)}')

    if isinstance(condition, Condition):
        return condition

    if isinstance(condition, Compare):
        return Condition(**{condition.name: condition})

    if condition is is_outer:
        return is_outer(string)

    return condition

    # import inspect

    # npar = len(inspect.signature(condition).parameters)
    # if npar == 1:
    #     return Condition(condition)

    # from recipes import pprint as pp
    # raise ValueError(f'Condition test function has incorrect signature: '
    #                  f'{pp.caller(condition)}')


def _match(string, brackets, must_close=False):

    left, right = brackets
    if left not in string:
        return (None, (None, None))

    # logger.debug('Searching {!r} in {!r}', brackets, string)

    # 'hello(world)()'
    pre, match = string.split(left, 1)
    # 'hello', 'world)()'
    open_ = 1  # current number of open brackets
    for i, m in enumerate(match):
        if m in brackets:
            open_ += (1, -1)[m == right]

        if open_ == 0:
            p = len(pre)
            return (match[:i], (p, p + i + 1))

    # land here if (outer) bracket unclosed
    if must_close == 1:
        raise ValueError(f'No closing bracket {right!r}.')

    if must_close == -1:
        i = string.index(left)
        return (string[i + 1:], (i, None))

    return (None, (None, None))


class BracketParser:
    """
    Class for matching, iterating, splitting, filtering, replacing pairs of
    brackets in strings.
    """

    def __init__(self, *pairs):
        """


        Parameters
        ----------
        pairs : str or tuple of str
            Characters or strings for opening and closing bracket. Must have
            length of 2.
        """
        if not pairs:
            pairs = ALL_BRACKET_PAIRS
        self.pairs = list(set(pairs))
        self.open, self.close = zip(*self.pairs)
        self._open_close = ''.join(self.open) + ''.join(self.close)

    # @ftl.lru_cache()
    def _index(self, string):
        # NOTE: line below reverses the operands:
        # >>> (c in self._open_close for c in string)
        for i in where(string, op.contained, self._open_close):
            yield i, string[i]

    def _iter(self, string, must_close=False):
        # TODO: filter level here to avoid unnecessary construction of
        # BracketPair and performance cost.
        assert must_close in {-1, 0, 1}

        positions = defaultdict(list)
        open_ = defaultdict(int)
        for j, b in self._index(string):
            if b in self.open:
                positions[b].append(j)
                open_[b] += 1
            else:
                o = PAIRED[b]
                open_[o] -= 1
                pos = positions[o]
                if pos:
                    i = pos.pop(-1)
                    yield BracketPair((o, b), string[i + 1:j], (i, j),
                                      len(positions[o]))
                elif must_close == 0:
                    yield BracketPair((o, b), None, (None, j), 0)

                elif must_close == 1:
                    raise ValueError(f'No opening bracket for: {b!r} at {j}.')
                # must_close == -1 doesn't yield anything
        #
        if must_close and any(positions.values()):
            pos, open_ = cofilter(op.not_, positions.values(), positions.keys())
            # pylint: disable=stop-iteration-return
            raise ValueError('No closing bracket for: '
                             f'{next(open_)!r} at {next(pos):d}')
            # +'; '.join(map('{!r:} at {:d}'.format, open_, pos)))

        for b, idx in positions.items():
            o = PAIRED[b]
            for i in idx:
                yield BracketPair((o, b), None, (i, None), 0)

    def match(self, string, must_close=False):
        """
        Find a matching pair of closed brackets in the string `s` and return the
        encolsed string as well as, optionally, the indices of the bracket pair.

        Will return only the first closed pair if the input string `s` contains
        multiple closed bracket pairs. To iterate over bracket pairs, use
        `iter_brackets`.

        If there are nested bracket inside `string`, only the outermost pair
        will be matched.

        If `string` does not contain the opening bracket, None is always
        returned.

        If `string` does not contain a closing bracket the return value will be
        `None`, unless `must_close` has been set in which case a ValueError is
        raised.


        Examples
        --------
        >>> s = 'def sample(args=(), **kws):'
        >>> r, (i, j) = BracketParser('()').match(s)
        ('args=(), **kws' , (10, 25))
        >>> r == s[i+1:j]
        True

        Returns
        -------
        BracketPair

        Raises
        ------
        ValueError if `must_close` is True and there is no matched closing
        bracket.
        """
        return next(self._iter(string, must_close), None)

    def iterate(self, string, must_close=False, condition=always_true,
                inside_out=True):
        """
        Parse `string` by finding pairs of brackets.

        Parameters
        ----------
        string : str
            String potentially containing pairs of (nested) brackets.
        must_close : {-1, 0, 1}
            Defines the behaviour for unclosed pairs of brackets:
            -1          : Silently ignore
             0 or False : Yield BracketPair with None at missing index
             1 or True  : raises ValueError

        Yields
        -------
        match : BracketPair
        """

        # get condition test call signature
        test = get_test(condition, string)
        # logger.debug('Iterating {!r} brackets in {!r} with condition: {}',
        #              self.brackets, string, condition)
        itr = filter(test, self._iter(string, must_close))
        if inside_out:
            yield from itr
            return

        levels = defaultdict(list)
        for match in itr:
            levels[match.level].append(match)

        for lvl in sorted(levels.keys()):
            yield from levels[lvl]

    def findall(self, string, must_close=False, condition=always_true,
                inside_out=True):
        """
        List all BracketPairs
        """
        return list(self.iterate(string, must_close, condition, inside_out))

    # def groupby(self, *attrs):

    def strip(self, string, condition=always_true):
        """
        Conditionally strip opening and closing brackets from the string. 

        See Also
        --------
        `replace` which replaces the enclosed string for each matched pair of
        brackets

        Parameters
        ----------
        s : str
            string to be stripped of brackets.


        Examples
        --------
        >>> strip('{{{{hello world}}}}')
        'hello world'

        Returns
        -------
        string
            The string with brackets stripped.
        """

        indices = set()
        for pair in self.iterate(string, condition=condition):
            indices.update(pair.indices)
        indices -= {None}
        return delete(string, indices)

    # def strip(self, string):
    #     """
    #     Strip all outermost paired brackets.

    #     return self.remove(string, condition=(level == 0))

    def _ireplace(self, string, sub, condition=always_true):
        start = 0
        for pair in self.iterate(string, condition=condition):
            yield string[start:pair.start]
            yield sub
            start = pair.end + 1
        yield string[start:]

    def replace(self, string, sub, condition=always_true):
        return ''.join(self._ireplace(string, sub, condition))

    def remove(self, string, condition=always_true):
        return self.replace(string, '', condition)

    # def switch():
    # change bracket type

    def split(self, string, must_close=False, condition=always_true):
        return list(self.isplit(string, must_close, condition))

    def isplit(self, string, must_close=False, condition=always_true):
        for pair in self.split2(string, must_close, condition):
            yield from filter(None, pair)

    def split2(self, string, must_close=False, condition=always_true):

        start = 0
        j = -1
        for match in self.iterate(string, must_close, condition, False):
            i, j = match.indices
            yield string[start:i], string[i:j+1]
            start = j + 1

        # no brackets
        if start == 0:
            yield (string, '')

        elif (j + 1) != len(string):
            yield (string[j + 1:], '')

    # alias
    split_paired = split2

    def depth(self, string):
        """
        Get the depth of the deepest nested pair of brackets.

        Parameters
        ----------
        string : str
            String containing (nested) brackets.
        depth : int, optional
            The starting depth, by default 0.

        Examples
        --------
        >>> braces.depth('0{1{2{3{4{5{6{7}}}}}}}')
        7

        Returns
        -------
        int
            Deepest nesting level.
        """
        depth = defaultdict(int)
        for match in self.iterate(string, must_close=True):
            depth[match.brackets] = max(depth[match.brackets], match.level + 1)

        if len(self.pairs) == 1:
            return depth.pop(tuple(self.pairs[0]), 0)

        return dict(depth)


# predifined parsers for specific pairs
braces = curly = BracketParser('{}')
parentheses = parens = round = BracketParser('()')
square = hard = BracketParser('[]')
chevrons = angles = BracketParser('<>')


# pylint: disable=missing-function-docstring
insert = {'Parameters[pair] as brackets': BracketParser}


# @doc.splice(BracketParser.match, insert)
def match(string, brackets, must_close=False):
    return BracketParser(brackets).match(string, must_close)


# @doc.splice(BracketParser.iterate, insert)
def iterate(string, brackets, must_close=False, condition=always_true):
    return BracketParser(brackets).iterate(string, must_close, condition)


# @doc.splice(BracketParser.remove, insert)
def remove(string, brackets, condition=always_true):
    return BracketParser(brackets).remove(string, condition)


# @doc.splice(BracketParser.strip, insert)
def strip(string, brackets):
    return BracketParser(brackets).strip(string)


# @doc.splice(BracketParser.depth, insert)
def depth(string, brackets):
    return BracketParser(brackets).depth(string)


def xsplit(string, brackets='{}', delimeter=','):
    """
    Conditional splitter. Split on delimeter only if its not enclosed by
    brackets.

    Parameters
    ----------
    string : str
        [description]
    brackets : str, optional
        [description], by default '{}'
    delimeter : str, optional
        [description], by default ','

    Examples
    --------
    >>> 

    Returns
    -------
    list
        [description]
    """
    # need this for bash brace expansion for nested braces

    # short circuit
    if brackets is None:
        return string.split(delimeter)

    #
    itr = BracketParser(brackets).split2(string, condition=(level == 0))
    collected = _xsplit_worker(*next(itr), delimeter)
    for pre, enclosed in itr:
        first, *parts = _xsplit_worker(pre, enclosed, delimeter)
        collected[-1] += first
        collected.extend(parts)
    return collected


def _xsplit_worker(pre, enclosed, delimeter):
    parts = pre.split(delimeter)
    parts[-1] += enclosed
    return parts


del insert
