"""
A cookbook for the python developer connoisseur 🧑🏽‍🍳🍷🐍.
"""

# third-party
from loguru import logger

# relative
from .utils import *
from .lists import cosort
from . import string
from . import functionals

# aliases
strings = string
functional = functionals

# silence logging by default
logger.disable('recipes')
