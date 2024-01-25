"""
Tools for parsing and editing strings containing (arbitrarily nested)
paired delimiters.
"""

# std
import math
import numbers
import warnings as wrn
import itertools as itt
from collections import defaultdict
from dataclasses import asdict, astuple, dataclass
from typing import Callable, Collection, List, Tuple, Union

# third-party
import more_itertools as mit

# relative
from .. import op
from ..iter import where
from ..functionals import always, echo, not_none
from . import delete, named_items, pluralize


# import docsplice as doc
# ---------------------------------------------------------------------------- #
# Braces(string) # TODO / .tokenize / .parse
# # __all__ = ['Parser', 'braces', 'square', 'round', 'chevrons']

# ---------------------------------------------------------------------------- #

ALL_BRACKET_PAIRS = {'()', '[]', '{}', '<>'}

INFINT = 2 ** 32
CARET = '^'


# utils
# ---------------------------------------------------------------------------- #


# def asdict(obj):
#     return dict(zip((slots := obj.__slots__), op.AttrGetter(*slots)(obj)))


def _resolve_max_split(max_split):
    if max_split in (-1, math.inf, None):
        return INFINT

    assert isinstance(max_split, numbers.Integral)
    assert max_split >= 0
    return int(max_split)  # copy


def sort_match(match):
    """Helper for sorting pairs of indices, either one of which may be None"""
    return match.start if match.end is None else match.end
    # if match.is_open():
    #     #
    #     o = (-1, 1)[match.indices.index(None)]
    #     return (next(filter(None, match.indices)), INFINT)[::o]

    # return match.indices


# exceptions
# ---------------------------------------------------------------------------- #
class UnpairedDelimiterWarning(Warning):
    pass


class UnpairedDelimiterError(ValueError):
    """
    Exception used when unpaired brackets encountered and `must_close=True`.
    """

    # def __init__(self, string, open_or_close, positions):
    #     super().__init__(self, string, open_or_close, positions)

    def __str__(self):
        string, open_or_close, positions = self.args
        return ''.join(
            (f'No {open_or_close} {pluralize("bracket", positions)} for: ',
             '\n'.join(f'{open_!r} at {named_items(pos, "position")}'
                       for open_, pos in positions.items()),
             show_unpaired(string, positions))
        )


def show_unpaired(string, positions, mark=CARET):

    if len(string) >= 100:
        return ''

    x = [' '] * (len(string) + 1)
    for _, pos in positions.items():
        for i in pos:
            x[i] = mark
        if not pos:
            x[-1] = mark

    return (f'\n> {string}'
            f'\n  {"".join(x)}')


# conditional matching
# ---------------------------------------------------------------------------- #

class _Condition:
    def __init__(self, name):
        self.name = str(name)

    def __repr__(self):
        return f'{type(self).__name__}({self.name})'


class AlwaysTrue:

    class _AlwaysTrue(_Condition):
        # Default condition test. Singleton. always returns True
        def __call__(self, *_, **__):
            return True

        def __repr__(self):
            return 'always(True)'

        def __copy__(self, *_):
            return AlwaysTrue._instance

        __deepcopy__ = __copy__

    _instance = _AlwaysTrue(True)

    def __new__(cls):
        return AlwaysTrue._instance


alwaysTrue = AlwaysTrue()


class IsOutermost(_Condition):
    """
    Conditional to check if brackets are outermost enclosing pair.
    """

    def __init__(self, string):
        self.n = len(string)

    def __call__(self, match):
        return (match.indices == (match.level, self.n - match.level - 1))


# alias
is_outer = IsOutermost


class AttributeTest(_Condition):
    # def __new__(cls, name='', func=None, *rhs):
    #     if func in AttributeCompare._symbols:
    #         return AttributeCompare

    #     return super().__new__(cls)

    def __init__(self, name, func):
        """
        Create a conditional for future comparison of attribute `name` of an
        object.

        Parameters
        ----------
        name : str
            Attribute name of object, the value of which will be compared.
        """
        assert callable(func)
        self.name = str(name)
        self.op = func

    def __call__(self, obj, *rhs):
        return self.op(getattr(obj, self.name), *rhs)

    def __repr__(self):
        return f'{type(self).__name__}: {self.op.__name__}(<o>.{self.name}, ...)'

# import functools as ftl


class AttributeConditional(_Condition):
    """
    Abstraction layer for delayed evaluation of comparison operators on
    object attribute `name`.

    Object which supports comparison operations "<"  "<="  "==" "=>"  ">".
    Comparing this object with another (eg. int), initializes a `AttributeCompare` which
    when called, will do the comparison between the value of the `name`
    attribute of the object which was passed, with the other object (eg int). 
    """

    def __eq__(self, rhs):
        return self._compare(op.eq, rhs)

    def __lt__(self, rhs):
        return self._compare(op.lt, rhs)

    def __le__(self, rhs):
        return self._compare(op.le, rhs)

    def __gt__(self, rhs):
        return self._compare(op.gt, rhs)

    def __ge__(self, rhs):
        return self._compare(op.ge, rhs)

    # @ftl.lru_cache()
    def _compare(self, op, rhs):
        return AttributeCompare(self.name, op, rhs)
        # id_ = (self.name, op, rhs)
        # if id_ not in self._cache:
        # self._cache[id_] = AttributeCompare(self.name, op, rhs)
        # return self._cache[id_]


# condition testing helpers
level = AttributeConditional('level')
indices = AttributeConditional('indices')
enclosed = AttributeConditional('enclosed')
delimiters = AttributeConditional('delimiters')


class AttributeCompare(AttributeTest):
    """
    Comparison operator wrapper for comparing variable lhs with fixed rhs.
    """
    _cache = {}
    _symbols = {op.eq: '==',
                op.lt: '<',
                op.le: '≤',
                op.gt: '>',
                op.ge: '≥'}

    # def __new__(cls, *args):
    #     if args in cls._cache:
    #         return cls._cache[args]

    #     obj = super().__new__(cls)
    #     cls._cache[args] = obj
    #     return

    def __init__(self, name, operator, rhs):
        super().__init__(name, operator)
        self.rhs = rhs

    def __eq__(self, value):
        if not isinstance(value, type(self)):
            return False

        getter = op.AttrGetter('name', 'op', 'rhs')
        return getter(self) == getter(value)

    def __call__(self, lhs):
        return self.op(getattr(lhs, self.name), self.rhs)

    def __str__(self):
        if symbol := self._symbols.get(self.op):
            return f'({self.name} {symbol} {self.rhs})'
        return f'{self.op}(<o>.{self.name}, {self.rhs})'

    __repr__ = __str__

    def _logic(self, op_, rhs):
        # boolean logic. return ChainedCompare instance
        if isinstance(rhs, ChainedCompare):
            rhs.args.append(self)
            rhs.ops.append(op_)
            return rhs

        if isinstance(rhs, AttributeCompare):
            return ChainedCompare((self, rhs), (op_,))

        raise TypeError(f'Invalid type {type(rhs)} encountered on right hand '
                        f'side while constructing `ChainedComparison` object.')

    def __or__(self, rhs):
        return self._logic(op.or_, rhs)

    def __and__(self, rhs):
        return self._logic(op.and_, rhs)


class ChainedCompare:  # ListOf(AttributeCompare)
    def __init__(self, comparers, logicals):
        self.comparers = comparers
        self.logicals = logicals  # operators

    def __call__(self, obj):
        # compute the sequence of comparisons
        first, *comparers = self.comparers
        #
        result = first(obj)
        for op_, cmp in zip(self.logicals, comparers):
            result = op_(result, cmp(obj))
        return result

# ---------------------------------------------------------------------------- #


@dataclass(eq=True, repr=False)  # slots=True #(3.10)
class ConditionTest:
    """
    Collection of conditional tests on Delimited attributes. Used for 
    filtering Delimited from iterable.
    """

    level:      Union[Callable, int] = alwaysTrue
    enclosed:   Union[Callable, str] = alwaysTrue
    indices:    Union[Callable, Collection[int]] = alwaysTrue
    delimiters: Union[Callable, Collection[str], str] = alwaysTrue

    def __post_init__(self):
        for key, val in asdict(self).items():
            if not isinstance(val, _Condition):
                if callable(val):
                    val = AttributeTest(key, val)
                else:
                    val = AttributeCompare(key, op.eq, val)

            #
            setattr(self, key, val)

    def __call__(self, match):
        # compare match attributes
        return all(check(match) for check in astuple(self))

    def __repr__(self):
        if components := (val for val in astuple(self) if val is not alwaysTrue):
            return f'{type(self).__name__}({" & ".join(map(str, components))})'

        return f'{type(self).__name__}({alwaysTrue})'


# alias
Condition = ConditionTest

# default (no filtering)
NoCondition = ConditionTest()
MustClose = ConditionTest(enclosed=not_none)
Level0 = ConditionTest(level=0)


def get_test(condition, string):
    """
    Function wrapper to support multiple call signatures for user defined
    condition tests.
    """
    if not callable(condition):
        raise TypeError(
            'Parameter `condition` should be a callable, or preferably a '
            f'`ConditionTest` object, not {type(condition)}.'
        )

    if isinstance(condition, ConditionTest):
        return condition

    if isinstance(condition, AttributeCompare):
        return ConditionTest(**{condition.name: condition})

    if condition is IsOutermost:
        return IsOutermost(string)

    return condition

    # import inspect

    # npar = len(inspect.signature(condition).parameters)
    # if npar == 1:
    #     return ConditionTest(condition)

    # from recipes import pprint as pp
    # raise ValueError(f'ConditionTest test function has incorrect signature: '
    #                  f'{pp.caller(condition)}')


# Matched Delimiters
# ---------------------------------------------------------------------------- #
@dataclass
class Delimited:
    """
    Object representing a pair of delimiters at some position and nesting level in
    a string, possibly enclosing some content.
    """

    delimiters: Tuple[str]
    """Characters or strings for opening and closing bracket. Must have length 2.
    Opening and closing characters should be unique, but other than that can be
    arbitrary strings."""
    enclosed: str
    """The enclosed sting. May be empty, or None in the case of unclosed 
    "pairs"."""
    indices: List[int] = (None, None)
    """Integer indices of opening- and closing bracket pairs within the sample 
    string. Either of the indices may be None."""
    level: int = 0
    """Depth of nesting."""

    @classmethod
    def null(cls):
        """
        Constructor for a non-existent Delimited to be used as sentinel.
        """
        return cls('{}', None, (None, None))

    def __post_init__(self):
        self.delimiters = tuple(self.delimiters)
        self.opening, self.closing = self.delimiters
        # self.start, self.end = self.indices

    def __iter__(self):
        yield self.enclosed
        yield self.indices

    def __str__(self):
        if self.enclosed is None:
            return '<UNCLOSED>'
        else:
            return self.enclosed.join(self.delimiters)

    def __bool__(self):
        return any((self.enclosed, *self.indices))

    @property
    def start(self):
        return self.indices[0]

    @property
    def end(self):
        return self.indices[1]

    # @ftl.cached_property
    # @property
    # def full(self):
    #     return self.enclosed.join(self.delimiters)

    def is_open(self):
        return None in self.indices

    def is_closed(self):
        return not self.is_open()


# ---------------------------------------------------------------------------- #

class Parser:
    """
    Class for matching, iterating, splitting, filtering, replacing paired
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

        self.pairs = list(set(pairs) or ALL_BRACKET_PAIRS)
        try:
            self.opening, self.closing = zip(*self.pairs)
        except Exception as err:
            import sys, textwrap
            from IPython import embed
            from better_exceptions import format_exception
            embed(header=textwrap.dedent(
                    f"""\
                    Caught the following {type(err).__name__} at 'delimited.py':466:
                    %s
                    Exception will be re-raised upon exiting this embedded interpreter.
                    """) % '\n'.join(format_exception(*sys.exc_info()))
            )
            raise
            
        self._open_close = ''.join(self.opening) + ''.join(self.closing)
        self.pair_map = pm = dict(pairs)
        self.pair_map.update(dict(zip(pm.values(), pm.keys())))
        self._unique_delimiters = (self.opening != self.closing)
        # self._unclosed_unordered = False

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
        # Delimited and possible performance cost.
        assert must_close in {-1, 0, 1}

        positions = defaultdict(list)
        open_ = defaultdict(int)
        for j, b in self._index(string):
            if b in self.opening and self._unique_delimiters:
                # opening bracket
                positions[b].append(j)
                open_[b] += 1
                # logger.debug('Opening bracket: {} at {}.', b, j)
            else:
                # closing bracket
                o = self.pair_map[b]
                open_[o] -= 1
                if pos := positions[o]:
                    i = pos.pop(-1)
                    yield Delimited((o, b), string[i + 1:j], (i, j),
                                    len(positions[o]))

                elif must_close == 0:
                    yield Delimited((o, b), None, (None, j), 0)

                elif must_close == 1:
                    raise UnpairedDelimiterError(string, 'opening', {b: j})

                # NOTE: `must_close == -1` doesn't yield anything, just continue

        # Handle unclosed brackets
        if (must_close == 1) and any(positions.values()):
            raise UnpairedDelimiterError(string, 'closing', positions)

        if must_close == -1:
            return

        # If we're here `must_close == 0`: fill None for missing bracket indices
        for b, idx in positions.items():
            # If opening and closing brackets are distinct characters:
            # Check if b is opening, Items will be unordered, we have to keep
            # track of the state if we want to deliver the pairs in a requested
            # order
            if (self.opening != self.closing and b in self.opening
                    and idx and idx != [len(string) + 1]):
                wrn.warn('Unclosed opening brackets in string. Items will be '
                         'out of order. Use the `findall` method for obtaining '
                         'an index-ordered list braces.', UnpairedDelimiterWarning)

            # opening, closing characters
            pair = tuple(sorted([b, self.pair_map[b]]))
            for i in idx:
                yield Delimited(pair, None, (i, None), 0)

    # TODO: must_close is the same as ConditionTest(enclosed=not_none)
    def iterate(self, string, must_close=False, condition=NoCondition,
                inside_out=False, outside_in=False):
        """
        Parse a string by finding (pairs of) (possibly nested) brackets.

        Parameters
        ----------
        string : str
            The string to be parsed. May contain (pairs of) brackets  .
        must_close : {-1, 0, 1}
            Defines the behaviour when an unclosed of bracket is encountered:
            -1          : Silently ignore
             0 or False : Yield Delimited with None at missing index
             1 or True  : raises ValueError

        Yields
        ------
        match : Delimited
        """

        # logger.debug('Iterating {!r} brackets in {!r} with condition: {}.',
        #              self.delimiters, string, condition)
        itr = self._iter(string, must_close)

        # if self._unclosed_unordered:
        #     itr = self._unclosed_reorder(itr) # pointless

        # get condition test call signature
        test = get_test(condition, string)

        # Check if condition requires `level`
        if ((must_close == 0) and
            (isinstance(test, IsOutermost) or
             (isinstance(test, ConditionTest) and (test.level is not alwaysTrue)))):
            # User asked for filter on `level`. Since `level` may change due to
            # unclosed braces, we have to unpack here if we have any unclosed.
            with wrn.catch_warnings():
                wrn.simplefilter('ignore', UnpairedDelimiterWarning)
                itr = filter(test, list(self._unclosed_reorder(itr)))

        else:
            itr = filter(test, itr)

        if inside_out or outside_in:
            levels = defaultdict(list)
            for match in itr:
                levels[match.level].append(match)

            for lvl in sorted(levels.keys(), reverse=inside_out):
                yield from levels[lvl]

            return

        # This just yield pairs at any level in the order that they are closed
        yield from itr

    # alias
    iter = iterate

    def _unclosed_reorder(self, itr):
        # NOTE:
        # Subtlety: The _iter method will not always yield brackets in left
        # right sequence if `must_close` is False:
        # eg: '(()'
        # In this case, it is ambiguous whether the first or middle bracket is
        # unclosed.
        # Since we traverse left right, we can only know the first bracket is
        # unclosed once we reached the end of the string, so the unclosed
        # bracket at index 0 will be yielded *after* the inner bracket

        # In this case we also have to fix the levels

        n_open = 0
        for match in sorted(itr, key=sort_match):
            if match.indices[1] is None:  # Open bracket with missing closing
                n_open += 1
            else:
                match.level -= n_open

            yield match

    def match(self, string, must_close=False, condition=NoCondition,
              inside_out=False, outside_in=True):
        """
        Search the string for a single (pair of) bracket(s). With the default
        parameters, this method returns the first (and outermost) bracket pair.
        The remaining parameters can be used to control which bracket (pair) will
        be matched, and whether unclosed brackets should be accepted.

        To iterate over multiple bracket pairs, use the `iterate` method.

        Parameters
        ----------
        string : _type_
            The string to search for a bracket pair.
        must_close : bool, optional
            _description_, by default False
        condition : _type_, optional
            _description_, by default NoCondition
        inside_out : bool, optional
            _description_, by default False
        outside_in : bool, optional
            _description_, by default True

        Parameters
        ----------
        string : str

        must_close : bool, optional
            Defines the behaviour for unclosed pairs of brackets:
            -1          : Silently ignore
             0 or False : Yield Delimited with None in place of missing 
                          start/stop index.
             1 or True  : raises ValueError

        Examples
        --------
        >>> s = 'def sample(args=(), **kws):'
        >>> r, (i, j) = Parser('()').match(s)
        ('args=(), **kws' , (10, 25))
        >>> r == s[i+1:j]
        True

        Returns
        -------
        Delimited

        Raises
        ------
        ValueError if `must_close` is True and there is no matched closing
        bracket.
        """

        # with ctx.suppress(UnpairedDelimiterError):
        return next(
            self.iterate(string, must_close, condition, inside_out, outside_in),
            None
        )

    def findall(self, string, must_close=False, condition=NoCondition,
                inside_out=False, outside_in=False):
        """
        List all Delimiteds
        """

        with wrn.catch_warnings(record=True) as warnings:
            wrn.simplefilter('always', UnpairedDelimiterWarning)

            # Unclosed opening braces will be yield out of order when iterating,
            # we have to keep track of the state if we want to deliver the pairs
            # in a requested order

            out = list(self.iterate(string, must_close, condition,
                                    inside_out, outside_in))
            # handle out of order unclosed
            if warnings:
                print(warnings)
                return list(self._unclosed_reorder(out))

        return out

    # ------------------------------------------------------------------------ #
    def strip(self, string, condition=NoCondition):
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

        current = 0
        recurse = condition in (NoCondition, Level0)
        if condition is NoCondition:
            condition = ConditionTest(level=0)

        matches = self.iterate(string, must_close=-1, condition=condition)
        if condition is IsOutermost:
            yield next(matches).enclosed
            return

        for delimited in matches:
            if delimited.start < current:
                continue

            yield string[current:delimited.start]

            out = make_sub(delimited.enclosed, *callable_args)
            if recurse:
                yield ''.join(self._ireplace(out, make_sub, condition, callable_args))
            else:
                yield out

            current = delimited.end + 1

        yield string[current:]

    def replace(self, string, sub, condition=NoCondition, callable_args=()):
        if isinstance(sub, str):
            sub = always(sub)
        elif not callable(sub):
            raise TypeError('Replacement value `sub` should be str or callable')

        return ''.join(self._ireplace(string, sub, condition, callable_args))

    def remove(self, string, condition=NoCondition):
        return self.replace(string, echo, condition)

    # def switch():
    # change bracket type
    # ------------------------------------------------------------------------ #
    def split(self, string, max_split=None, must_close=False, condition=Level0):
        if string:
            return list(self.isplit(string, max_split, must_close, condition))
        return ['']

    def isplit(self, string, max_split=None, must_close=False, condition=NoCondition):
        return filter(None, self._isplit(string, max_split, must_close, condition))

    def _isplit(self, string, max_split, must_close, condition):
        # iterate sub strings for (pre-bracket, bracketed) parts of string
        max_split = _resolve_max_split(max_split)
        if max_split == 0:
            yield string
            return

        slices = self.islices(string, must_close, condition)
        for sec in itt.islice(slices, max_split - 1):
            yield string[sec]

        yield string[sec.stop:]

    def isplit_indices(self, string,  must_close=False, condition=NoCondition):

        yield 0

        j = -1
        for match in self.iterate(string, must_close, condition):
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

    def islices(self, string, must_close=False, condition=NoCondition):
        yield from itt.starmap(
            slice, self._isplit_index_pairs(string, must_close, condition))

    def _isplit_slice_pairs(self, string, must_close, condition):
        # for splitting like (pre-bracket, bracketed)
        slices = self.islices(string, must_close, condition)
        yield from mit.grouper(slices, 2, fillvalue=slice(len(string), None))

    def isplit_pairs(self, string, must_close=False, condition=NoCondition):
        for pre, bracketed in self._isplit_slice_pairs(string, must_close, condition):
            yield string[pre], string[bracketed]

    def split_pairs(self, string, must_close=False, condition=NoCondition):
        return list(self.isplit_pairs(string, must_close, condition))

    def csplit(self, string, seperator=',',  max_split=None):
        """
        Conditional splitter. Split on `seperator` only if it is not enclosed by
        `brackets`. Does not go deeper than level 0, so enclosed delimited
        substrings are ignored.

        Parameters
        ----------
        string : str
            [description]
        brackets : str, optional
            [description], by default '{}'
        seperator : str, optional
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
            pre, *parts = string[pre].split(seperator, max_split - len(collected) + 1)
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
        return string.split(seperator, max_split)

    def rcsplit(self, string, seperator=',',  max_split=None):
        # HACK
        from recipes.string import sub

        inverses = dict((*zip(braces.opening, braces.closing),
                         *zip(braces.closing, braces.opening)))
        reversed_ = self.csplit(sub(string[::-1], inverses), seperator, max_split)
        return [sub(rev[::-1], inverses) for rev in reversed(reversed_)]

    # ------------------------------------------------------------------------ #

    def has_unclosed(self, string):
        return any((None in match.indices)
                   for match in self._iter(string, must_close=False))

    def encloses(self, string):
        return string.startswith(self.opening) and string.endswith(self.closing)

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
            depth[match.delimiters] = max(depth[match.delimiters], match.level + 1)

        if len(self.pairs) == 1:
            return depth.pop(tuple(self.pairs[0]), 0)

        return dict(depth)
    

# ---------------------------------------------------------------------------- #
# predifined parsers for specific pairs
braces = curly = Parser('{}')
parentheses = parens = round = Parser('()')
square = hard = Parser('[]')
chevrons = angles = Parser('<>')

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
# insert = {'Parameters[pair] as brackets': Parser}


# @doc.splice(Parser.match, insert)
def match(string, delimiters, must_close=False, condition=NoCondition):
    return Parser(delimiters).match(string, must_close, condition)


# @doc.splice(Parser.iterate, insert)
def iterate(string, delimiters, must_close=False, condition=NoCondition):
    return Parser(delimiters).iterate(string, must_close, condition)


# @doc.splice(Parser.remove, insert)
def remove(string, delimiters, condition=NoCondition):
    return Parser(delimiters).remove(string, condition)


# @doc.splice(Parser.strip, insert)
def strip(string, delimiters):
    return Parser(delimiters).strip(string)


# @doc.splice(Parser.depth, insert)
def depth(string, delimiters):
    return Parser(delimiters).depth(string)


# @doc.splice(Parser.depth, csplit)
def csplit(string, delimiters='{}', seperator=',', max_split=None):
    # need this for bash brace expansion for nested braces

    # short circuit
    if delimiters is None:
        return string.split(seperator)

    return Parser(delimiters).csplit(string, seperator, max_split)


# alias
xsplit = csplit


# def _csplit_worker(pre, bracketed, delimiter, max_split):
#     parts = pre.split(delimiter, max_split)
#     parts[-1] += bracketed
#     return parts

# del insert
