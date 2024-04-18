
"""
A collection of some awesome functional decorators used accross many recipes.
"""


# from .path import path
# from .expose import expose

# these imports enable the following usage pattern:
# from decor import expose
# @expose.args
# def foo():
#     ...

# TODO: REALLY NEED A DECORATOR that can flag all methods in a class

from .oo import Singleton, sharedmethod
from .base import Decorator, Factory, Wrapper
from .core import (delayed, ignore_params, ignore_returns, update_defaults,
                   upon_first_call)
