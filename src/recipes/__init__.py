"""
A cookbook for the python developer connoisseur 🧑🏽‍🍳🍷🐍.
"""

# third-party
from loguru import logger

# relative
from . import functionals, string
from .utils import *
from .lists import cosort


# aliases
strings = string
functional = functionals

# silence logging by default
logger.disable('recipes')
