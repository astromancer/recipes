
# std
import multiprocessing as mp

# third-party
from joblib.parallel import Parallel, delayed

# local
from recipes.flow.contexts import ContextStack
from recipes.concurrence.joblib import initialized


# ---------------------------------------------------------------------------- #
memory_lock = mp.Lock()


# ---------------------------------------------------------------------------- #
def set_lock(lock):
    # Initialize each process with a global variable lock.
    print('process setup')
    global memory_lock
    memory_lock = lock


def work(*args, **kws):
    print('doing work:', args, kws)


def get_workload():
    yield from range(10)


def test_main(njobs=10):

    worker = delayed(work)
    context = ContextStack()
    executor = Parallel(njobs, verbose=10)
    context.add(initialized(executor, set_lock, (memory_lock, )))
    with context as compute:
        compute(worker(data) for data in get_workload())
