import time

from decor.profile import profiler

@profiler.histogram
def foo():
    time.sleep(0.1)
    time.sleep(0.2)
    time.sleep(0.3)
    time.sleep(0.5)
    time.sleep(0.3)
    time.sleep(0.2)
    time.sleep(0.1)

foo()