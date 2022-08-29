"""
Tools for parsing and editing strings containing (nested) brackets.
"""

# std
import math
import numbers
import itertools as itt
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Callable, Collection, List, Tuple, Union

# third-party
import more_itertools as mit

# relative
from .. import op
from ..iter import where
from ..functionals import always, echo0
from . import delete


# import docsplice as doc


# Braces(string) # TODO / .tokenize / .parse
# # __all__ = ['BracketParser', 'braces', 'square', 'round', 'chevrons']

ALL_BRACKET_PAIRS = ('()', '[]', '{}', '<>')

SYMBOLS = {op.eq: '==',
           op.lt: '<',
           op.le: '≤',
           op.gt: '>',
           op.ge: '≥'}

INFINT = 2 ** 32
CARET = '^'
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


def _resolve_max_split(max_split):
    if max_split in (-1, math.inf, None):
        return INFINT

    assert isinstance(max_split, numbers.Integral)
    assert max_split >= 0
    return int(max_split)  # copy


def show_unpaired(self, string, positions, caret=CARET):

    if len(string) >= 100:
        return ''

    x = [' '] * (len(string) + 1)
    for _, pos in positions.items():
        for i in pos:
            x[i] = caret
        if not pos:
            x[-1] = caret

    return (f'\n> {string}'
            f'\n  {"".join(x)}')

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
    """Characters or strings for opening and closing bracket. Must have length 2."""
    enclosed: str
    indices: List[int] = (None, None)
    """Indices of opening- and closing bracket pairs."""
    level: int = 0

    @classmethod
    def null(cls):
        return cls('{}', None, (None, None))

    def __post_init__(self):
        self.brackets = tuple(self.brackets)
        self.open, self.close = self.brackets
        self.start, self.end = self.indices

    def __iter__(self):
        yield self.enclosed
        yield self.indices

    def __str__(self):
        return '<UNCLOSED>' if self.enclosed is None else self.enclosed

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
            'Parameter `condition` should be a callable, or preferably a '
            f'`Condition` object, not {type(condition)}.'
        )

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


# class ErrorStateHandler:
#     def __init__(self, gen):
#         self.gen = gen

#     def __iter__(self):
#         self.value = yield from self.gen


class BracketParser:
    """
    Class for matching, iterating, splitting, filtering, replacing pairs of
    delimiters in strings.
    """

    def __init__(self, *pairs):
        """


        Parameters
        ----------
        pairs : str or tuple of str
            Characters or strings for opening and closing bracket. Each pair of
            brackets must be an object of length 2.
        """
        if not pairs:
            pairs = ALL_BRACKET_PAIRS
        self.pairs = list(set(pairs))
        self.open, self.close = zip(*self.pairs)
        self._open_close = ''.join(self.open) + ''.join(self.close)
        self.pair_map = pm = dict(pairs)
        self.pair_map.update(dict(zip(pm.values(), pm.keys())))

    def __repr__(self):
        return f'{self.__class__.__name__}({self.pairs})'

    # @ftl.lru_cache()
    def _index(self, string):
        # NOTE: line below reverses the operands:
        # >>> (c in self._open_close for c in string)
        for i in where(string, op.contained, self._open_close):
            yield i, string[i]

    def _iter(self, string, must_close=0):
        # TODO: filter level here to avoid unnecessary construction of
        # BracketPair and possible performance cost.
        assert must_close in {-1, 0, 1}

        positions = defaultdict(list)
        open_ = defaultdict(int)
        for j, b in self._index(string):
            if b in self.open:
                positions[b].append(j)
                open_[b] += 1
                # logger.debug('Opening bracket: {} at {}', b, j)
            else:
                o = self.pair_map[b]
                open_[o] -= 1
                if pos := positions[o]:
                    i = pos.pop(-1)
                    yield BracketPair((o, b), string[i + 1:j], (i, j),
                                      len(positions[o]))
                elif must_close == 0:
                    yield BracketPair((o, b), None, (None, j), 0)

                elif must_close == 1:
                    raise ValueError(f'No opening bracket for: {b!r} at {j}.\n'
                                     f'{show_unpaired(string, positions)}')
                    # must_close == -1 doesn't yield anything

        # Handle unclosed brackets
        if (must_close == 1) and any(positions.values()):
            raise ValueError(
                'No closing brackets for: '
                + '\n'.join(f'{open_!r} at {pos}'
                            for open_, pos in positions.items())
                + self.show_unpaired(string, positions)
            )

        if must_close == -1:
            return

        # Fill None for missing bracket indices
        for b, idx in positions.items():
            pair = tuple(sorted([b, self.pair_map[b]]))
            for i in idx:
                yield BracketPair(pair, None, (i, None), 0)

    def match(self, string, must_close=False, condition=always_true):
        """
        Find a matching pair of closed brackets in the string `string` and
        return the encolsed string as well as, optionally, the indices of the
        bracket pair.

        Will return only the first (and outermost) closed pair if the input
        string `string` contains multiple closed bracket pairs. To iterate over
        bracket pairs, use `iter_brackets`.

        Parameters
        ----------
        string : str
            The string to search for a bracket pair.
        must_close : bool, optional
            Defines the behaviour for unclosed pairs of brackets:
            -1          : Silently ignore
             0 or False : Yield BracketPair with None in place of missing 
                          start/stop index.
             1 or True  : raises ValueError

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

        return next(self.iterate(string, must_close, condition), None)

    def iterate(self, string, must_close=False, condition=always_true,
                inside_out=False, outside_in=False):
        """
        Parse `string` by finding pairs of brackets.

        Parameters
        ----------
        string : str
            A string potentially containing pairs of (possibly nested) brackets.
        must_close : {-1, 0, 1}
            Defines the behaviour when an unclosed of bracket is encountered:
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

        if inside_out or outside_in:
            levels = defaultdict(list)
            for match in itr:
                levels[match.level].append(match)

            for lvl in sorted(levels.keys(), reverse=inside_out):
                yield from levels[lvl]

            return

        # Subtlety: The _iter method will not always yield brackets in left
        # right sequence if `must_close` is False:
        # eg: '(()'
        # In this case, it is ambigous whether the first or middle bracket is
        # unclosed.
        # Since we traverse left right, we can only know the first bracket is
        # unclosed once we reached the end of the string, so the
        # unclosed bracket at index 0 will be yielded *after* the inner bracket

        # with ctx.suppress(RuntimeError):
            # Iterable `itr` might be empty, in which case we can ignore the
            # RuntimeError and just return

        # try:
        #     itr = next(itr)
        # except RuntimeError as err:
        #     from IPython import embed
        #     embed(header="Embedded interpreter at 'src/recipes/string/brackets.py':446")

        if not must_close:
            itr = sorted(itr, key=op.attrgetter('indices'))

        # This just yield pairs at any level from left to right in the string
        yield from itr

    def findall(self, string, must_close=False, condition=always_true,
                inside_out=False, outside_in=False):
        """
        List all BracketPairs
        """
        return list(self.iterate(string, must_close, condition,
                                 inside_out, outside_in))

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

    def _ireplace(self, string, make_sub, condition, callable_args):
        start = 0
        for pair in self.iterate(string, condition=condition):
            yield string[start:pair.start]
            yield make_sub(pair.enclosed, *callable_args)
            start = pair.end + 1
        yield string[start:]

    def replace(self, string, sub, condition=always_true, callable_args=()):
        if isinstance(sub, str):
            sub = echo0
        elif not callable(sub):
            raise TypeError('Replacement value `sub` should be str or callable')

        return ''.join(self._ireplace(string, sub, condition, callable_args))

    def remove(self, string, condition=always_true):
        return self.replace(string, '', condition)

    # def switch():
    # change bracket type

    def split(self, string, max_split=None, must_close=False, condition=always_true):
        if string:
            return list(self.isplit(string, max_split, must_close, condition))
        return ['']

    def isplit(self, string, max_split=None, must_close=False, condition=always_true):
        return filter(None, self._isplit(string, max_split, must_close, condition))

    def _isplit(self, string, max_split, must_close, condition):
        # iterate sub strings for (pre-bracket, bracketed) parts of string
        max_split = _resolve_max_split(max_split)
        if max_split == 0:
            yield string
            return

        slices = self.isplit_slices(string, must_close, condition)
        for sec in itt.islice(slices, max_split - 1):
            yield string[sec]

        yield string[sec.stop:]

    def isplit_indices(self, string,  must_close=False, condition=always_true):

        yield 0

        j = -1
        for match in self.iterate(string, must_close, condition, False):
            i, j = match.indices
            yield i
            yield j + 1

        if (j + 1) != (n := len(string)):
            yield n

    def _isplit_index_pairs(self, string, must_close, condition):
        # for building slices to split the string
        indices = self.isplit_indices(string, must_close, condition)
        index_pairs = mit.pairwise(indices)
        if (first := next(index_pairs, None)) is None:
            yield (0, None)
            return

        yield from itt.chain([first], index_pairs)

    def isplit_slices(self, string, must_close=False, condition=always_true):
        yield from itt.starmap(
            slice, self._isplit_index_pairs(string, must_close, condition))

    def _isplit_slice_pairs(self, string, must_close, condition):
        # for splitting like (pre-bracket, bracketed)
        slices = self.isplit_slices(string, must_close, condition)
        yield from mit.grouper(slices, 2, slice(len(string), None))

    def isplit_pairs(self, string, must_close=False, condition=always_true):
        for pre, bracketed in self._isplit_slice_pairs(string, must_close, condition):
            yield string[pre], string[bracketed]

    def split_pairs(self, string, must_close=False, condition=always_true):
        return list(self.isplit_pairs(string, must_close, condition))

    def csplit(self, string, delimiter=',',  max_split=None):
        """
        Conditional splitter. Split on `delimiter` only if it is not enclosed by
        `brackets`. Does not go deeper than level 0, so enclosed delimited
        substrings are ignored.

        Parameters
        ----------
        string : str
            [description]
        brackets : str, optional
            [description], by default '{}'
        delimiter : str, optional
            [description], by default ','

        Examples
        --------
        >>> 

        Returns
        -------
        list
            [description]
        """
        max_split = _resolve_max_split(max_split)
        if max_split == 0:
            return [string]

        # iterate slices for (pre-bracket, bracketed) parts of string
        collected = ['']
        for pre, bracketed in self._isplit_slice_pairs(string, True, (level == 0)):
            pre, *parts = string[pre].split(delimiter, max_split - len(collected) + 1)
            collected[-1] += pre
            collected.extend(parts)
            collected[-1] += string[bracketed]

            if len(collected) > max_split:
                if bracketed.stop:  # not at the end of the string yet!
                    collected[-1] += string[bracketed.stop:]
                return collected

        if collected:
            return collected

        # no brackets
        return string.split(delimiter, max_split)

    def rcsplit(self, string, delimiter=',',  max_split=None):
        # HACK
        from recipes.string import sub

        inverses = dict((*zip(braces.open, braces.close),
                         *zip(braces.close, braces.open)))
        reversed_ = self.csplit(sub(string[::-1], inverses), delimiter, max_split)
        return [sub(rev[::-1], inverses) for rev in reversed(reversed_)]

    # ------------------------------------------------------------------------ #

    def has_unclosed(self, string):
        return any((None in match.indices)
                   for match in self._iter(string, must_close=False))

    def encloses(self, string):
        return string.startswith(self.open) and string.endswith(self.close)

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

parsers = {
    '{':  braces,
    '{}': braces,
    '[':  square,
    '[]': square,
    '(':  round,
    '()': round,
    '<':  chevrons,
    '<>': chevrons
}

# pylint: disable=missing-function-docstring
# insert = {'Parameters[pair] as brackets': BracketParser}


# @doc.splice(BracketParser.match, insert)
def match(string, brackets, must_close=False, condition=always_true):
    return BracketParser(brackets).match(string, must_close, condition)


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


# @doc.splice(BracketParser.depth, csplit)
def csplit(string, brackets='{}', delimiter=',', max_split=None):
    # need this for bash brace expansion for nested braces

    # short circuit
    if brackets is None:
        return string.split(delimiter)

    return BracketParser(brackets).csplit(string, delimiter, max_split)


# alias
xsplit = csplit


# def _csplit_worker(pre, bracketed, delimiter, max_split):
#     parts = pre.split(delimiter, max_split)
#     parts[-1] += bracketed
#     return parts

# del insert
