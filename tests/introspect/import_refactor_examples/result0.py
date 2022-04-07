
# std
import os
import re
import mmap
import this
import time
import datetime
import operator
import antigravity
import itertools as itt
from copy import copy
from typing import Union, ClassVar
from dataclasses import dataclass, field
from collections import namedtuple, OrderedDict

# third-party
import numpy as np
import more_itertools as mit
import astropy.io.fits as pyfits
from astropy.io.fits.hdu import HDUList, PrimaryHDU
from IPython import embed

# local
import recipes.iter as itr
from recipes.io import warn
from recipes.list import sorter
from recipes.set import OrderedSet
from recipes.dict import AttrReadItem
from recipes.logging import LoggingMixin
from recipes.parallel.synced import SyncedArray, SyncedCounter
import motley
from motley.table import Table as sTable
from motley.profiler.timers import timer
from motley.profiler.imports import (ImportFinder, ModuleExtractor,
                                     ImportExtractor)

# relative
from .header import shocHeader
from .filenaming import NamingConvention
from .utils import retrieve_coords, convert_skycooords
from .convert_keywords import KEYWORDS as kw_old_to_new
from .timing import timingFactory, Time, get_updated_iers_table, fmt_hms
# import logging


# WARNING: THESE IMPORT ARE MEGA SLOW!! ~10s  (localize to mitigate?)
# import matplotlib.pyplot as plt


# TODO: choose which to use for timing: spice or astropy
# from .io import InputCallbackLoop

# debugging


def whatwhat():
    import some.nested.local


