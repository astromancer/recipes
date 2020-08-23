"""
A collection of awesome decorators
"""

# from .path import path
from .expose import expose

# these imports enable the following usage pattern:
# from decor import expose
# @expose.args
# def foo():
#     ...


def raises(kind):
    def _raises(msg):
        raise kind(msg)
    return _raises