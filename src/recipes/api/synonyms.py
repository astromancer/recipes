"""
Parameter and Keyword name translation for understanding inexact human input.

Say you have an API function:

>>> def stamp(labeled=True, color='default', center=False):
...     'does a thing'

Your users might reasonably attempt the following:
>>> stamp(centre=True, colour='green', labelled='order 66')
unwittingly having used a variant spelling of the parameter names that is
natural to their local. This will of course lead to an error. Unless...

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

# Keyword translation on-the-fly for flexible, typo tollerant APIs.
# If you are like me, and often misremember keyword arguments for classes or
# functions, (especially those with giant signatures [1,2,3]), this module will
# help you! It matches your typo to the actual API keyword, and corrects your
# mistake with an optional logged notification.
# # TODO You can also issue deprecation notifications


# std
import re
import inspect
import itertools as itt

# third-party
from loguru import logger

# relative
from ..functionals import Emit
from ..decorators import Decorator
from ..string.brackets import BracketParser


def _ordered_group(word):
    return '|'.join(itt.accumulate(word)).join(('()'))


def _unordered_group(word):
    return word.join('[]') + f'{{0,{len(word)}}}'


OPTION_REGEX_BUILDERS = {'[]': _ordered_group,
                         '()': _unordered_group}


class RegexTranslate:
    """
    Class to assist many-to-one keyword mappings via regex pattern matching.
    """

    def __init__(self, pattern, answer=''):  # ensure_order

        # assert mode in {'simple', 'regex', None}, f'Invalid mode string: {mode!r}'

        self.answer = str(answer)

        if isinstance(pattern, str):
            self.regex = re.compile(pattern)

        elif isinstance(pattern, re.Pattern):
            self.regex = pattern

        else:
            raise TypeError('Invalid pattern type: {}', type(pattern))

    def __call__(self, s):
        if self.regex.fullmatch(s):
            return self.answer

    def __repr__(self):
        return f'{self.__class__.__name__}({self.regex.pattern} --> {self.answer})'


class KeywordTranslate(RegexTranslate):
    """
    Implements a basic pattern matching syntax to match incomplete words.
    Optional characters that need to appear in order should be enclosed in
    square brackets eg: "n[umbe]r". This pattern will match "number" as well
    as "numr" and "nr", but not "nuber". Optional characters that can have
    any order should be enclosed in round brackets eg: "frivol(ou)s".

    Note that input patterns are translated to regex, so eg:
        "n[umber]" --> "n(u|um|umb|umbe|umber)" "n(u(m(b(e(r?)?)?)?)?)?"
        "n(umbe)r" --> "n(umbe)?r"
    Any other regex syntax in the pattern will pass through unaltered. You 
    can use this to your advantage. For example to match a single optional
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
    >>> resolve = KeywordTranslate('n[umbe]r[_rows]', 'row_nrs')
    >>> resolve('number_rows')
    'row_nrs'
    >>> resolve('nr_rows')
    'row_nrs'
    >>> resolve('nrs')
    'row_nrs'
    """

    parser = BracketParser('[]', '()')

    def __init__(self, pattern, answer=''):
        super().__init__(self._build_regex(pattern), answer)

    def _build_regex(self, pattern):
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
            # FIXME: nesting?
            sub = sub[i1 + 1:]

            # print(sub, regex)
            # i += 1
        return regex


POS, PKW, VAR, KWO, VKW = inspect._ParameterKind


class Synonyms(Decorator):
    """
    Decorator for function parameter translation.
    """
    # TODO: detect ambiguous mappings

    def __init__(self, mappings=(), /, mode='regex', action='warn'):
        # TODO **kws for simple mappings labels=label
        self.emit = Emit(action, TypeError)
        self.resolvers = []
        self.update(mappings, mode)
        self.func = None
        self._param_names = ()

    def __call__(self, func):
        self.func = func
        self.signature = sig = inspect.signature(func)
        self._param_names = tuple(sig.parameters.keys())
        self._no_kws = (inspect._ParameterKind.VAR_KEYWORD in
                         {p.kind for p in sig.parameters.values()})
        if self._no_kws:
            self.logger.info(f'No variadic keywords in {self.func}. Changing'
                             f' function signature!')
        
        # decorate
        return super().__call__(func, kwsyntax=self._no_kws)

    def __wrapper__(self, func, *args, **kws):
        
        if self._no_kws:
            args, kws = self.resolve(args, kws)
            return func(*args, **kws)

        try:
            return func(*args, **kws)
        except TypeError as err:  # NOTE: only works if func has no variadic kws
            if ((e := str(err)).startswith(func.__name__) and
                    ('unexpected keyword argument' in e)):
                #
                logger.debug('Caught {}\n. Attempting keyword translation.', err)
                args, kws = self.resolve(args, kws)
                logger.debug('Re-trying function call {}(...) with synonymous '
                             'keywords.', func.__name__)
                return func(*args, **kws)
            raise

    def __repr__(self):
        return repr(self.resolvers)

    def update(self, mappings=(), /, _mode='regex'):
        """
        Update the translation map.
        """

        translator = TRANSLATORS[_mode]
        for pattern, target in dict(mappings).items():
            # if isinstance(k, str)
            self.resolvers.append(translator(pattern, target))

    def resolve(self, args, kws):    # namespace=None,
        """
        Translate the keys in `kws` dict to the correct one for the hard api.
        """
        sig = self.signature
        param_types = {par.name: par.kind
                       for par in sig.parameters.values()}

        # resolve kws
        kws = {self.resolve_key(key): val
               for key, val in kws.items()}

        new = []
        args = iter(args)
        for (name, kind) in param_types.items():
            if kind in (KWO, VKW):
                break

            new.append(kws.pop(name) if name in kws else next(args, ()))

        new.extend(args)
        return new, kws

    # @ftl.lru_cache()
    def resolve_key(self, key):
        if key in self._param_names:
            return key

        for func in self.resolvers:
            if (trial := func(key)) in self._param_names:
                logger.debug(msg := f'Keyword translated: {key!r} --> {trial!r}')
                self.emit(msg)
                return trial

        return key

        # raise KeyError(f'Invalid parameter {key!r} for {describe(self.func)}')


# alias
synonyms = Synonyms

TRANSLATORS = {'simple': KeywordTranslate,
               'regex': RegexTranslate}
