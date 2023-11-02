

# third-party
from joblib._parallel_backends import MultiprocessingBackend, SequentialBackend

# relative
from ..functionals import noop


def initialized(self, f_init=noop, args=(), **kws):
    # HACK for custom process initializer for joblib.Parallel
    # Adapted from:
    # https://github.com/joblib/joblib/issues/381#issuecomment-480910348

    if isinstance(self._backend, SequentialBackend):
        return self

    if isinstance(self._backend, MultiprocessingBackend):
        self._backend_args.update(initializer=f_init, initargs=args)
        return self

    if not hasattr(self._backend, '_workers'):
        self.__enter__()

    workers = self._backend._workers
    origin_init = workers._initializer

    def new_init():
        if callable(origin_init):
            origin_init()

        f_init(*args, **kws)

    workers._initializer = new_init

    return self
