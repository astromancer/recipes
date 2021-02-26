"""
Some common decorators used accross recipes
"""


def negate(func):
    def wrapped(obj):
        return not func(obj)
    return wrapped
