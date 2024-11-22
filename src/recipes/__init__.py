"""
A cookbook for the python developer connoisseur 🧑🏽‍🍳🍷🐍.
"""

# std
from importlib.metadata import version

# third-party
from loguru import logger

# silence logging by default
logger.disable('recipes')

# relative
from . import functionals, string
from .string import regex
from .config import create_user_config
from .containers import (cosort, dicts, duplicate_if_scalar, is_scalar, lists,
                         not_null, sets)


# ---------------------------------------------------------------------------- #

# version
__version__ = version('recipes')


# aliases
strings = string
functional = functionals


# Create user config file if needed
user_config_path = create_user_config('config.yaml', __file__, 
                                      version_stamp=__version__)
