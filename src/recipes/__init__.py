"""
A cookbook for the python developer connoisseur 🧑🏽‍🍳🍷🐍.
"""

# std
from importlib.metadata import PackageNotFoundError, version

# third-party
from loguru import logger

# relative
from . import functionals, string
from .utils import *
from .lists import cosort
from .config import create_user_config


__version__ = version('recipes')


# aliases
strings = string
functional = functionals


# Create user config file if needed
user_config_path = create_user_config('config.yaml', __file__,
                                      version_stamp=__version__)


# silence logging by default
logger.disable('recipes')
