"""
Miscellaneous decorators
"""


# TODO add usage patterns to all these classes!!!


import functools


class singleton:
    # adapted from:
    # https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html
    
    def __init__(self, klass):
        self.klass = klass
        self.instance = None

    def __call__(self, *args, **kws):
        if self.instance is None:
            self.instance = self.klass(*args, **kws)
        return self.instance



def upon_first_call(do_first):
    
    def decorator(func):
        func._ran = False
        
        def wrapper(self, *args, **kwargs):
            if not func._ran:
                do_first(self)
            
            results = func(self, *args, **kwargs)
            func._ran = True
            return results

        return wrapper

    return decorator

# def do_first(q):
# print( 'DOING IT', q )

# class Test:

# @upon_first_call( do_first )
# def bar( self, *args ) :
# print( "normal call:", args )

# test = Test()
# test.bar()
# test.bar()
