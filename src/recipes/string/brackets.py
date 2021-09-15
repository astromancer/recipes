
# std
import math
import inspect
import numbers
import itertools as itt

# local
import docsplice as doc

# relative
from . import remove_affix
from ..functionals import always, echo0

__all__ = ['Brackets', 'braces', 'square', 'round', 'chevrons']

# Braces(string) # TODO / .tokenize / .parse

# function that always returns True
always_true = always(True)


def outermost(string, brackets, indices, _ignored):
    i, j = indices
    return remove_affix(string, *brackets) == string[i+1:j]


class Yielder:
    """
    Helper class for iterating items while optionally yielding their index
    positions in the sequence.
    """

    def __init__(self, return_index):
        self.yields = self._with_index if return_index else echo0

    def __call__(self, inside, i, j, start):
        return self.yields(inside, i, j, start)

    # @staticmethod
    # def _without_index(inside, *ignored_):
    #     return inside

    @staticmethod
    def _with_index(inside, i, j, start):
        return inside, (start + i, start + j)


class Brackets:
    """
    Class representing a pair of brackets
    """

    def __init__(self, pair):
        """
        Object representing a pair of brackets

        Parameters
        ----------
        pair : str or tuple of str
            Characters or strings for opening and closing bracket. Must have
            length of 2.
        """
        self.brackets = self.open, self.close = pair

    def __iter__(self):
        yield from self.brackets

    def match(self, string, return_index=True, must_close=False):
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

        Parameters
        ----------
        string : str
            The string to parse.
        return_index : bool
            Whether to return the indices where the brackets where found.
        must_close : int
            Controls behaviour on unmatched bracket pairs.
            If 1 or True:
                ValueError will be raised
            if 0 or False:
                All unclosed brackets are ignored. ie. `None` will be returned
                even if there is an opening bracket.
            If -1:
                Partial matches are allowed and the partial string beginning one
                character after the opening bracket will be returned. In this
                case, if `return_index` is True, the index of the closing brace
                position will take the value None.

        Examples
        --------
        >>> s = 'def sample(args=(), **kws):'
        >>> r, (i, j) = Brackets('()').match(s)
        ('args=(), **kws' , (10, 25))
        >>> r == s[i+1:j]
        True

        Returns
        -------
        match : str or None
            The enclosed str index: tuple or None (start, end) indices of the
            actual brackets that were matched

        Raises
        ------
        ValueError if `must_close` is True and there is no matched closing
        bracket

        """

        null_result = None
        if return_index:
            null_result = (None, (None, None))

        left, right = self.brackets
        if left not in string:
            return null_result

        # if right not in string:
        #     return null_result

        # 'hello(world)()'
        pre, match = string.split(left, 1)
        # 'hello', 'world)()'
        open_ = 1  # current number of open brackets
        for i, m in enumerate(match):
            if m in self.brackets:
                open_ += (1, -1)[m == right]
            if not open_:
                if return_index:
                    p = len(pre)
                    return match[:i], (p, p + i + 1)
                return match[:i]

        # land here if (outer) bracket unclosed
        if must_close == 1:
            raise ValueError(f'No closing bracket {right}')

        if must_close == -1:
            i = string.index(left)
            if return_index:
                return string[i + 1:], (i, None)
            return string[i + 1:]

        return null_result

    def iter(self, string, return_index=True, must_close=False,
             condition=always_true):
        """
        Iterate through consecutive (non-nested) closed bracket pairs.

        Parameters
        ----------
        string : str
            String potentially containing pairs of (nested) brackets.
        return_index : bool, optional
            Whether to yield the indices of opening- closing bracket pairs,
            by default Tru

        Yields
        -------
        inside : str
            The string enclosed by matched bracket pair
        indices : (int, int)
            Index positions of opening and closing bracket pairs.
        """

        # get condition test call signature
        test = get_test(condition)
        # get yield function
        yields = Yielder(return_index)

        nr = 0
        start = 0
        while True:
            inside, (i, j) = self.match(string[start:], True, must_close)
            # print(f'{string=}, {inside=}, {start=}, {i=}, {j=}')
            if inside is None:
                break

            # condition
            if test(string, self.brackets, (i, j), nr):
                yield yields(inside, i, j, start)

            # increment
            nr += 1
            start += (j + 1)

    def iter_nested(self, string, return_index=True, condition=always_true,
                    depth=..., inside_out=True, level=0, pos=0):

        if isinstance(depth, numbers.Integral):
            right_depth = (depth == level)
        elif depth is ...:
            right_depth = True
        else:
            raise ValueError('Depth should be an integer or an Ellipsis ...')

        yields = Yielder(return_index)

        iters = []
        # start = 0
        for inside, (i, j) in self.iter(string, True, True, condition):
            itr = self.iter_nested(inside, return_index, condition, depth,
                                   inside_out, level + 1, pos + i + 1)
            if inside_out:
                # unpack from inside out
                yield from itr
            else:
                iters.append(itr)

            if right_depth:
                # print(f'!!{inside!r} {pos=} {i=} {j=}')
                # print(f'!!{string[i+1:j]!r}')
                # print(string[i+1:j] == inside)
                yield yields(inside, i, j, pos)

        # print('chaining', iters)
        yield from itt.chain(*iters)
        # print('DONE', level)

    def enclose(self, string):
        return string.join(self.brackets)

    def encloses(self, string):
        """
        Conditional test for fully enclosed string.

        Parameters
        ----------
        string : str
            String to check

        Examples
        --------
        >>>
        """
        inner = self.match(string, False)
        return remove_affix(string, *self.brackets) == inner

    def remove(self, string, depth=math.inf, condition=always_true):
        """
        Removes arbitrary number of closed bracket pairs from a string up to
        requested depth.

        Parameters
        ----------
        s : str
            string to be stripped of brackets.


        Examples
        --------
        >>> unbracket('{{{{hello world}}}}')
        'hello world'

        Returns
        -------
        string
            The string with all enclosing brackets removed.
        """

        return self._remove(string, get_test(condition), depth)

    def _remove(self, string, test=always_true, depth=math.inf, level=0, nr=0):
        # return if too deep
        if level >= depth:
            return string

        # testing on sequence number for every element is probably less efficient
        # than slicing the iterator below. Can think of a good way of
        # implementing that? is there even use cases?

        out = ''
        nr = -1
        pre = 0
        itr = self.iter(string, condition=test)
        for nr, (inside, (i, j)) in enumerate(itr):
            out += string[pre:i]
            out += self._remove(inside, test, depth, level+1, nr)
            pre = j + 1

        # did the loop run?
        if nr == -1:
            return string

        return out + string[j + 1:]

    def strip(self, string):
        """
        Strip outermost brackets

        Parameters
        ----------
        string
            The string with outermost enclosing brackets removed.
        """
        self.remove(string, condition=outermost)

    def split(self, string):

        if not string:
            yield [string]
            return

        itr = self.iter(string)
        start = 0
        for _, (i, j) in itr:
            if i != start:
                yield string[start:i]
            # if i != j + 1:
            yield string[i:j+1]
            start = j + 1

        if start != len(string):
            yield string[start:]

    def split2(self, string):

        start = 0
        j = -1
        for _, (i, j) in self.iter(string):
            yield string[start:i], string[i:j+1]
            start = j + 1

        if start == 0:
            yield (string, '')

        elif j + 1 != len(string):
            yield (string[j + 1:], '')

    def depth(self, string, depth=0):
        deepest = depth
        for sub in self.iter(string, False, True):
            deepest = max(deepest, self.depth(sub, depth + 1))
        return deepest


def get_test(condition):
    # function wrapper to support multiple call signatures for user defined
    # condition test
    npar = len(inspect.signature(condition).parameters)
    if npar == 4:
        return condition

    if npar == 1:
        def test(string, brackets, indices, nr):
            i, j = indices
            return condition(string[i+1:j])
        return test

    raise ValueError('Condition test function has incorrect signature')


# predifined bracket types
braces = curly = Brackets('{}')
parentheses = parens = round = Brackets('()')
square = hard = Brackets('[]')
chevrons = angles = Brackets('<>')

#
insert = {'Parameters[pair] as brackets': Brackets}


@doc.splice(Brackets.match, insert)
def match(string, brackets, return_index=True, must_close=False):
    return Brackets(brackets).match(string, return_index, must_close)


@doc.splice(Brackets.iter, insert)
def iterate(string, brackets, return_index=True, must_close=False,
            condition=always_true):
    return Brackets(brackets).iter(string, return_index, must_close, condition)


@doc.splice(Brackets.remove, insert)
def remove(string, brackets, depth=math.inf, condition=always_true):
    return Brackets(brackets).remove(string, depth, condition)


@doc.splice(Brackets.strip, insert)
def strip(string, brackets):
    return Brackets(brackets).strip(string)


def xsplit(string, brackets='{}', delimeter=','):
    # conditional splitter. split on delimeter only if its not enclosed by
    # brackets. need this for nested brace expansion a la bash
    # Brackets

    itr = Brackets(brackets).split2(string)

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
