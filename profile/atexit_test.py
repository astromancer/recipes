import time
import atexit

def foo():
    print('\n\n\nJOLLY GOOD!')

atexit.register(foo)

time.sleep(1)
# raise ValueError