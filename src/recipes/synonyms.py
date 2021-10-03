"""
Functional keyword translation for understanding inexact input from humans 
"""

# Keyword translation on-the-fly for flexible APIs.
# If you are like me, and often misremember keyword arguments for classes or
# functions, (especially those with giant signatures [1,2,3]), this module will
# help you! It matches your typo to the actual API keyword, and corrects your
# mistake with an optional logged notification.


# std
import re
import warnings

# local
from recipes.string.brackets import BracketParser

# relative
from .decorators import Decorator
from .functionals import noop, raises


class KeywordTranslator:
    """
    Class to assist many-to-one keyword mappings via regex pattern matching.
    """
    parser = BracketParser('[]')

    def __init__(self, pattern, answer=None):
        """

        Parameters
        ----------
        pattern
        answer

        Example
        -------
        >>> tr = KeywordTranslator('n[umbe]r[_rows]', 'row_nrs')
        >>> tr('number_rows')
        'row_nrs'
        >>> tr('nr_rows')
        'row_nrs'
        >>> tr('nrs')
        'row_nrs'
        """

        regex = ''
        self.answer = ''
        self.pattern = pattern
        sub = pattern
        while 1:
            match = self.parser.match(sub, must_close=True)
            if match is None:
                regex += sub
                break

            # print(s, i0, i1)
            s = match.enclosed
            i0, i1 = match.indices
            # FIXME: this regex not exactly correct for optional characters
            # 'n[umbe]r[_rows]' -> n(umber)?r(_rows)?
            regex += f'{sub[:i0]}[{s}]{{0,{len(s)}}}'
            self.answer += sub[:i0]
            sub = sub[i1 + 1:]

            # print(sub, regex)
            # i += 1
        self.regex = re.compile(regex)

        if answer:
            self.answer = answer  # str(answer)

    def __call__(self, s):
        if self.regex.fullmatch(s):
            return self.answer

    def __repr__(self):
        return f'{self.__class__.__name__}({self.pattern} --> {self.answer})'


class Synonyms(Decorator):
    """
    Decorator for keyword translation.
    """
    _actions = {-1: noop,              # silently ignore invalid types
                0: warnings.warn,            # emit warning
                1: raises(TypeError)}     # raise TypeError
    _default_action = -1
    emit = staticmethod(_actions[_default_action])

    # TODO: detect ambiguous mappings

    def __init__(self, mappings=None, **kws):
        self.mappings = []
        self.update(mappings, **kws)
        self.func = None

    def __repr__(self):
        return repr(self.mappings)

    def __wrapper__(self, func, *args, **kws):
        return func(*args, **self.resolve(**kws))

    def update(self, mappings=None, **kws):
        for k, v in dict(mappings, **kws).items():
            # if isinstance(k, str)
            self.mappings.append(KeywordTranslator(k, v))

    def resolve(self, namespace=None, **kws):
        """
        Map typo/terse keywords in `kws` to their correct form. If given, values
        from the `namespace` dict replace those in kws if their corresponging
        keywords are valid parameter names for `func` and they are non-default
        values.
        """
        # get arg names and defaults
        # TODO: use inspect.signature here ?
        func = self.func
        code = func.__code__
        defaults = func.__defaults__
        arg_names = code.co_varnames[1:code.co_argcount]

        # load the defaults / passed args
        n_req_args = len(arg_names) - len(defaults)
        # opt_arg_names = arg_names[n_req_args:]

        params = {}
        # now get non-default arguments (those passed by user)
        if namespace is not None:
            for i, o in enumerate(arg_names[n_req_args:]):
                v = namespace[o]
                if v is not defaults[i]:
                    params[o] = v

        # resolve terse kws and add to dict
        for k, v in kws.items():
            if k in arg_names:
                continue

            for m in self.mappings:
                trial = m(k)
                if trial in arg_names:
                    self.emit('Keyword translated: %r --> %r', k, trial)
                    params[trial] = v
                    break
            else:
                # get name
                name = getattr(func, '__qualname__', func.__name__)
                raise KeyError(f'{k!r} is not a valid keyword for {name!r}')

        # `params` now has keys which are the correct parameter names for
        # self.func. `params` values are either the function default or user input
        # value from namespace or kws.

        return params
