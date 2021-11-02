"""
Parameter and Keyword name translation for understanding inexact human inputself.

Say you have an API function:

>>> def stamp(labeled=True, color='default', center=False):
...     'does a thing'

Your users might attempt the following:
>>> stamp(centre=True, colour='green', labelled='order 66')
unwittingly having used a variant spelling of the parameter names that is
natural to theor local. This will of course lead to an error. Unless...

We can teach out function these alternatives like so:
>>> @api.synonymns(dict(
...     labeled ='labell?ed',
...     color   ='colou?r[ed]',
...     center  ='cent[er|re]'
... ))
... def stamp(labeled=True, color='default', center=False):
...     'the usual definition goes here'

Now, like magic, our function will work with the alternatives we gave it via the
regexes above at the cost of a small overhead for each misspelled parameter.
"""

# Keyword translation on-the-fly for flexible APIs.
# If you are like me, and often misremember keyword arguments for classes or
# functions, (especially those with giant signatures [1,2,3]), this module will
# help you! It matches your typo to the actual API keyword, and corrects your
# mistake with an optional logged notification.


# std
import re
import inspect
import itertools as itt

# third-party
from loguru import logger

# relative
from ..dicts import groupby
from ..decorators import Decorator
from ..string.brackets import BracketParser


def _ordered_group(word):
    return '|'.join(itt.accumulate(word)).join(('()'))


def _unordered_group(word):
    return word.join('[]') + f'{{0,{len(word)}}}'


OPTION_REGEX_BUILDERS = {'[]': _ordered_group,
                         '()': _unordered_group}


class KeywordTranslator:
    """
    Class to assist many-to-one keyword mappings via regex pattern matching.
    """
    parser = BracketParser('[]', '()')

    def __init__(self, pattern, answer=''):  # ensure_order
        """
        Implements a basic pattern matching syntax to match incomplete words.
        Optional characters that need to appear in order should be enclosed in
        square brackets eg: "n[umbe]r". This pattern will match "number" as well
        as "numr" and "nr", but not "nuber". Optional characters that can have
        any order should be enclosed in round brackets eg: "frivol(ou)s".

        Note that input patterns are translated to regex, so eg:
            "n[umbe]r" --> "n(u|um|umb|umbe)r"
            "n(umber)" --> "n[umber]{0,5}"
        Any other regex syntax in the pattern will pass through unaltered. You 
        can use this to your adbvantage. For example to match a single optional
        optional character, either enclose it in round brackets, or append a "?"
        eg: "col(_)head" and "col_?head" both work to match the optional
        underscore.

        Parameters
        ----------
        pattern : str
            Pattern for matching parameter / keyword names.
        answer: str
            The desired translation target.

        Example
        -------
        >>> resolve = KeywordTranslator('n[umbe]r[_rows]', 'row_nrs')
        >>> resolve('number_rows')
        'row_nrs' 
        >>> resolve('nr_rows')
        'row_nrs'
        >>> resolve('nrs')
        'row_nrs'
        """

        self.pattern = pattern
        self.answer = str(answer)
        sub = pattern
        regex = ''
        while 1:
            match = self.parser.match(sub, must_close=True)
            if match is None:
                regex += sub
                break

            # print(s, i0, i1)
            i0, i1 = match.indices
            s = OPTION_REGEX_BUILDERS[''.join(match.brackets)](match.enclosed)
            # regex for optional characters
            # 'n[umbe]r[_rows]' -> n(umber)?r(_rows)?

            regex += f'{sub[:i0]}{s}?'
            # self.answer += sub[:i0]
            sub = sub[i1 + 1:]

            # print(sub, regex)
            # i += 1
        self.regex = re.compile(regex)

    def __call__(self, s):
        if self.regex.fullmatch(s):
            return self.answer

    def __repr__(self):
        return f'{self.__class__.__name__}({self.pattern} --> {self.answer})'


POS, PKW, VAR, KWO, VKW = inspect._ParameterKind


class Synonyms(Decorator):
    """
    Decorator for function parameter translation.
    """
    # emit = Emit

    # TODO: detect ambiguous mappings

    def __init__(self, mappings=(), /, _emit=-1, **kws):
        self.emit = logger.debug    # Emit(_emit)
        self.resolvers = []
        self.update(mappings, **kws)
        self.func = None
        self._param_names = ()

    def __repr__(self):
        return repr(self.resolvers)

    def __wrapper__(self, func, *args, **kws):
        self.func = func
        self.signature = inspect.signature(func)
        self._param_names = tuple(self.signature.parameters.keys())

        args, kws = self.resolve(args, kws)
        return func(*args, **kws)

    def update(self, mappings=(), **kws):
        """
        Update the translation map.
        """
        for directive, target in dict(mappings, **kws).items():
            # if isinstance(k, str)
            self.resolvers.append(KeywordTranslator(directive, target))

    def resolve(self, args, kws):  # namespace=None,
        """
        Map the input keywords in `kws` to their correct form. If given, values
        from the `namespace` dict replace those in kws if their corresponging
        keywords are valid parameter names for `func` and they are non-default
        values.
        """
        # get arg names and defaults
        # bound = self.signature.bind_partial(*args)
        params = self.signature.parameters.values()
        # _, args = cogroup(params, args, key=op.attrgetter('kind'))
        groups = groupby(zip(args, params), lambda p: p[1].kind)
        args = next(zip(*groups.get(POS, ()), *groups.get(VAR, ())), ())

        # for key, val in kws.items():
        #     key = self.resolve_key(key)

        # func = self.func
        # code = func.__code__
        # defaults = func.__defaults__
        # arg_names = code.co_varnames[1:code.co_argcount]

        # load the defaults / passed args
        # n_req_args = len(arg_names) - len(defaults)
        # opt_arg_names = arg_names[n_req_args:]

        # params = {}
        # now get non-default arguments (those passed by user)
        # if namespace is not None:
        #     for i, argname in enumerate(arg_names[n_req_args:]):
        #         if (val := namespace[argname]) is not defaults[i]:
        #             params[argname] = val

        # resolve terse kws and add to dict
        kws = {**{p.name: val for val, p in groups.get(PKW, {})},
               **{self.resolve_key(key): val for key, val in kws.items()}}
        return args, kws

        # `params` now has keys which are the correct parameter names for
        # self.func. `params` values are either the function default or user
        # input value from namespace or kws.
        # return params

    # @ftl.lru_cache()
    def resolve_key(self, key):
        if key in self._param_names:
            return key

        for func in self.resolvers:
            if (trial := func(key)) in self._param_names:
                self.emit(f'Keyword translated: {key!r} --> {trial!r}')
                return trial

        return key

        # raise KeyError(f'Invalid parameter {key!r} for {describe(self.func)}')
