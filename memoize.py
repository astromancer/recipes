import atexit
import functools
import logging
from pathlib import Path

from recipes.io import load_pickle, save_pickle


class to_file(object):  # TODO: use DecoratorBase here?
    """Persistant memoizer that saves cache to file upon program termination"""

    def __init__(self, filename):
        filepath = Path(filename).expanduser()
        filename = str(filepath)

        if filepath.exists():
            # load existing cache
            logging.info('Loading cache at %r', filename)
            self._cache = load_pickle(filename)
            logging.debug('Cache contains %d entries', len(self._cache))
        else:
            # no existing cache. create.  this will only happen the first time the function executes
            logging.info('Creating cache at %r', filename)
            self._cache = {}

        self._save = False
        atexit.register(self.save, filename, self._cache)
        # FIXME: doesn't work in interactive session - do in thread?

    def save(self, filename, cache):
        if self._save:
            logging.info('Saving cache at %r', filename)
            save_pickle(filename, cache)

    def __call__(self, func):

        # TODO: maybe emit warning if func takes keywords. also non-hashable defaults
        # TODO: use functools.rlu_cache to limit cache size

        @functools.wraps(func)
        def memoizer(*args):
            # NOTE: DOES NOT SUPPORT KEYWORDS#, **kws):
            # NOTE: it is generally impossible to correctly memoize something that depends on non-hashable arguments
            # convert to string
            key = str(args)  # + str(kws)     #isinstance(args, Hashable)
            if key not in self._cache:
                self._cache[key] = func(*args)
                self._save = True
            return self._cache[key]

        return memoizer


class memoize():
    """
    Decorator that caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not re-evaluated).
    """

    def __init__(self, func):
        self.func = func  # can also be a method?
        self.cache = {}

    def __call__(self, *args, **kws):

        # if not isinstance(args, collections.Hashable):
        ## uncacheable. a list, for instance.
        ## better to not cache than blow up.
        # return self.func(*args)

        # arguments may not be hashable. Convert them to strings first.
        # NOTE: This will not work for objects that do not have unique string representations call to call
        key = str(args) + str(kws)

        if key in self.cache:
            return self.cache[key]
        else:
            value = self.func(*args)
            self.cache[key] = value
            return value

    def __repr__(self):
        """Return the function's docstring."""
        return self.func.__doc__

    def __get__(self, obj, objtype):
        """Support object methods."""
        return functools.partial(self.__call__, obj)

    to_file = to_file