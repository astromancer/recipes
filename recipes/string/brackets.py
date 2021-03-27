import inspect
import math
from . import remove_affix
import docsplice as doc

__all__ = ['Brackets', 'braces', 'square', 'round', 'chevrons']
# Braces(string).iter / .tokenize / .parse / match / strip / split
# ( )
# Parentheses
# or
# round brackets


# { }
# Braces
# or
# curly brackets

# [ ]
# Brackets
# or
# square brackets

#
# ⟨ ⟩
# Chevrons
# or
# angle brackets


def always_true(_):
    return True

# TODO: nested bracket iterator


class contained:
    def __init__(self, item):
        self.item = item

    def within(self, container):
        return self.item in container


def outermost(string, brackets, indices, nr):
    i, j = indices
    return remove_affix(string, *brackets) == string[i+1:j]


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
            Controls behaviour on unmatched bracket pairs. If 1 or True a
            ValueError will be raised, if 0 or False `None` will be returned
            even if there is an opening bracket.  If -1, partial matches are
            allowed and the partial string beginning one character after the
            opening bracket will be returned. In this case, if `return_index` is
            True, the index of the closing brace position will take the value
            None.

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
        if return_index:
            def yields(inside, i, j):
                return inside, (start + i, start + j)
        else:
            def yields(inside, i, j):
                return inside

        # get condition test call signature
        test = get_test(condition)

        start = 0
        nr = 0
        while True:
            inside, (i, j) = self.match(string, True, must_close)
            if inside is None:
                break

            # condition
            if test(string, self.brackets, (i, j), nr):
                yield yields(inside, i, j)

            # increment
            nr += 1
            start = j + 1
            string = string[start:]

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


def get_test(condition):
    # function wrapper to support multiple call signatures for user defined
    # condition test
    npar = len(inspect.signature(condition).parameters)
    if npar == 4:
        return condition

    elif npar == 1:
        def test(string, brackets, indices, nr):
            i, j = indices
            return condition(string[i+1:j])
    else:
        raise ValueError('Condition test function has incorrect signature')

    return test


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


# def _iter(string, brackets='()', return_index=True, must_close=False,
#                   condition=always_true, depth=math.inf, level=0):
#     """
#     Iterate through consecutive (non-nested) closed bracket pairs.

#     Parameters
#     ----------
#     string : [type]
#         [description]
#     brackets : str, optional
#         [description], by default '()'
#     return_index : bool, optional
#         [description], by default True

#     Yields
#     -------
#     [type]
#         [description]
#     """
#     if return_index:
#         def yields(inside, i, j):
#             return inside, (start + i, start + j)
#     else:
#         def yields(inside, i, j):
#             return inside

#     start = 0
#     while True:
#         inside, (i, j) = match_brackets(string, brackets, True, must_close)
#         if inside is None:
#             break

#         if condition(inside):
#           # THIS WILL UNPACK FROM THE INNERMOST OUTWARDS
#            yield from _iter(inside, )

#         start = j + 1
#         string = string[start:]


# def _iter_deep(string, brackets, return_index=True, must_close=False,
#                    condition=always_true, depth=math.inf, level=0):
#     # return if too deep
#     if level > depth:
#         return string

#     # inside, (i, j) = match_brackets(string, brackets, must_close=False)
#     # if inside is None or not condition(inside):
#     #     return string

#     tail = string[i:]
#     ran = False
#     for inside, (i, j) in iter_brackets(tail, brackets, return_index, must_close,
#                                         condition, level, level):
#         # THIS WILL UNPACK FROM THE INNERMOST OUTWARDS
#         yield from iter_brackets(inside, brackets, return_index, must_close,
#                                   condition, depth, level+1)
#         ran = True

#     if not ran:
#         yield inside


# #
#     itr = iter_brackets(string, brackets, condition=test)
#     try:
#         inside, (i, j) = next(itr)
#     except StopIteration:
#         return string
#     else:
#         out = string[:i]
#         tail = string[j + 1:]
#         nr = -1
#         for nr, (inside, _) in enumerate(itr):
#             out += _unbracket(inside, brackets, test, depth, level + 1, nr)

#         # did the loop run?
#         if nr > -1: # yes
#             return out + tail

#         # no? recurse on whatever is inside the brackets
#         return out + _unbracket(inside, brackets, test, depth, level + 1, nr) + tail


# # # alternatively
#     inside, (i, j) = match_brackets(string, brackets, must_close=False)
#     if inside is None or not test(inside, (i, j), nr):
#         return string

#     # testing on sequence number for every element is probably less efficient
#     # than slicing the iterator below. Can think of a good way of
#     # implementing that? is there even use cases?
#     # if condition is outermost:

#     out = string[:i]
#     tail = string[i:]
#     ran = False
#     itr = iter_brackets(tail, brackets, must_close=True, condition=test)
#     for nr, (inside, (i, j)) in enumerate(itr):
#         out += _unbracket(inside, brackets, test, depth, level+1, nr)
#         ran = True

#     if not ran:
#         out += inside

#     return out + tail[j + 1:]

# def to_fstring(string):
#"'%s(xy=(%g, %g), ' % (self.__class__.__name__, *self.center)"
# ---> 'self.__class__.__name__ + '(xy=(%g, %g), ' % self.center'
