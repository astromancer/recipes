"""
Process initializer for joblib.
"""

# third-party
from joblib._parallel_backends import MultiprocessingBackend, SequentialBackend

# relative
from ..functionals import noop


def initialized(self, initializer=noop, args=(), **kws):
    """
    Custom per-process process initialization for `joblib.Parallel`.

    Parameters
    ----------
    initializer : callable, optional
        Your process initializer, by default noop, which does nothing.
    args : tuple, optional
        Parameters for your initializer, by default ()

    Examples
    --------
    ... import multiprocessing as mp
    ... from joblib.parallel import Parallel, delayed
    ...
    ...
    ... memory_lock = mp.Lock()
    ...
    ... def set_lock(lock):
    ...     # Initialize each process with a global variable lock.
    ...     print('process setup')
    ...     global memory_lock
    ...     memory_lock = lock
    ...
    ... def work(*args, **kws):
    ...     print('doing work:', args, kws)
    ... 
    ... def get_workload():
    ...     yield from range(10)
    ...
    ... njobs = 10
    ... worker = delayed(work)
    ... context = ContextStack()
    ... executor = Parallel(njobs, verbose=10)
    ... context.add(initialized(executor, set_lock, (memory_lock, )))
    ... with context as compute:
    ...     compute(worker(data) for data in get_workload())

    [Parallel(n_jobs=10)]: Using backend LokyBackend with 10 concurrent workers.
    process setup
    doing work: (0,) {}
    doing work: (1,) {}
    doing work: (2,) {}
    [Parallel(n_jobs=10)]: Done   3 out of  10 | elapsed:    2.6s remaining:    6.0s
    doing work: (3,) {}
    doing work: (4,) {}
    [Parallel(n_jobs=10)]: Done   5 out of  10 | elapsed:    2.6s remaining:    2.6s
    doing work: (5,) {}
    doing work: (6,) {}
    [Parallel(n_jobs=10)]: Done   7 out of  10 | elapsed:    2.6s remaining:    1.1s
    doing work: (7,) {}
    process setup
    doing work: (8,) {}
    doing work: (9,) {}
    [Parallel(n_jobs=10)]: Done  10 out of  10 | elapsed:    2.6s finished
    process setup
    process setup
    process setup
    process setup
    process setup
    process setup
    process setup
    process setup


    Returns
    -------
    joblib.Parallel

    """
    # Adapted from:
    # https://github.com/joblib/joblib/issues/381#issuecomment-480910348

    if isinstance(self._backend, SequentialBackend):
        return self

    if isinstance(self._backend, MultiprocessingBackend):
        self._backend_args.update(initializer=initializer, initargs=args)
        return self

    if not hasattr(self._backend, '_workers'):
        self.__enter__()

    workers = self._backend._workers
    original_init = workers._initializer

    def new_init():
        if callable(original_init):
            original_init()

        initializer(*args, **kws)

    workers._initializer = new_init

    return self
