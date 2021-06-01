import this, antigravity  # maketh, one, fly
import os
import re
import mmap
import time
import datetime
# import logging
import operator
from copy import copy
import itertools as itt
from collections import namedtuple, OrderedDict
from typing import Union, ClassVar

from dataclasses import dataclass, field

# WARNING: THESE IMPORT ARE MEGA SLOW!! ~10s  (localize to mitigate?)
import numpy as np
# import matplotlib.pyplot as plt
import astropy.io.fits as pyfits
from astropy.io.fits.hdu import HDUList, PrimaryHDU
import more_itertools as mit

import recipes.iter as itr
from recipes.io import warn
from recipes.set import OrderedSet
from recipes.list import sorter
from recipes.logging import LoggingMixin
from recipes.dict import AttrReadItem
from motley.table import Table as sTable
from recipes.parallel.synced import (SyncedArray,
                                     SyncedCounter)

from motley.profiler.imports import ImportFinder, ModuleExtractor, \
    ImportExtractor

# TODO: choose which to use for timing: spice or astropy
# from .io import InputCallbackLoop
from .utils import retrieve_coords, convert_skycooords
from .timing import timingFactory, Time, get_updated_iers_table, fmt_hms
from .header import shocHeader
from .convert_keywords import KEYWORDS as kw_old_to_new
from .filenaming import NamingConvention

# debugging
from IPython import embed
from motley.profiler.timers import timer  # , profiler


def whatwhat():
    import some.nested.local


import motley