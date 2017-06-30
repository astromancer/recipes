import atexit
import functools
from pathlib import Path

from decor.base import OptionalArgumentsDecorator
from decor.expose import SameLineDone
from recipes.io import load_pickle, save_pickle


# def same_line_done():


class persistant_memoizer():
    """memoizer that saves cache to file at program termination"""

    def __init__(self, filename, verbose=True):  # TODO: use decoratorbase here?
        filepath = Path(filename).expanduser()
        filename = str(filepath)
        decorator = SameLineDone if verbose else OptionalArgumentsDecorator
        create_cache = decorator('Creating cache at %s' % filename)(lambda: {})
        load_cache = decorator('Loading cache at %s' % filename, 'Done')(load_pickle)
        self._save_cache = decorator('Saving cache at %s\n' % filename, 'Done')(save_pickle)

        if filepath.exists():
            # load existing cache
            self._cache = load_cache(filename)
        else:
            # no existing cache. create.  this will only happen the first time the function executes
            self._cache = create_cache()

        self._save = False
        atexit.register(self.save, filename, self._cache)  # NOTE: will not be saved on unnatural exit

    def save(self, filename, cache):
        if self._save:
            self._save_cache(filename, cache)

    def __call__(self, func):
        @functools.wraps(func)
        def memoizer(*args):
            # NOTE: DOES NOT SUPPORT KEYWORDS#, **kws):
            # NOTE: it is generally impossible to correctly memoize something that depends on non-hashable arguments
            # convert to string
            key = str(args)  # + str(kws)     #isinstance(args, Hashable)
            if key not in self._cache:
                self._cache[key] = func(*args)  # , **kws)
                self._save = True
            return self._cache[key]

        return memoizer



@persistant_memoizer('~/work/.test_cache')
def foo(n):
    return n*2

for i in range(10):
    foo(i)
    foo(i)
