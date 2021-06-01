import ast
import textwrap
from recipes.introspect.imports import ImportCapture, tidy, tidy_source
from pathlib import Path


def test_detect_decorator():
    source = textwrap.dedent("""\
    from foo import bar
    
    @bar
    def _():
        pass
    """)

    imp = ImportCapture(filter_unused=True)
    imp.visit(ast.parse(source))
    assert 'bar' in imp.used_names


def test_preserve_scope():
    source = textwrap.dedent("""\
    def _():
        from foo import bar
        bar()
    """)
    s = tidy_source(source, unscope=False)
    assert s == source


def test_merge_import_lines():
    source = textwrap.dedent(
        """\
        from matplotlib.collections import LineCollection
        from matplotlib.collections import EllipseCollection
        """)
    s = tidy_source(source, filter_unused=False)
    assert s == "from matplotlib.collections LineCollection, EllipseCollection"


def test_relative_imports():
    source = textwrap.dedent("""\
    from .. import CompoundModel, FixedGrid
    
    class MyModel(FixedGrid, CompoundModel):
        pass
    """)


# def test_capture_line_limit():
#     imp = ImportCapture(filter_unused=False)
#     imp.visit(ast.parse(source))

# TODO:
#  test_make_groups
#  test_filter_unused
#  test_sort_aesthetic
#  test_sort_alphabetic
#  test_multiline_imports
#  test_keep_comments
#  test_style_preference

def test_example():
    answer = tidy('example.py', dry_run=True)
    expected = Path('example_new.py').read_text()
    assert answer == expected

"""
import multiprocessing as mp
import os, re, this, antigravity  # single line multi-module
import socket
import sys
from multiprocessing.managers import SyncManager as Syncrotron
from pathlib import Path

import logging.handlers

from ...some.thing import footastic  # relative
from . import king

import numpy as np
from scipy import ndimage, spatial
from joblib.pool import MemmapingPool as MemmappingPool
from addict.addict import Dict
import more_itertools as mit

from obstools.phot.utils import rand_median
from obstools.phot.utils import rand_median  # duplicate
from obstools.phot.proc import FrameProcessor
from obstools.modelling.utils import load_memmap_nans
from obstools.phot.utils import rand_median  # triplicate

from recipes.interactive import is_interactive
from recipes.parallel.synced import SyncedCounter

import slotmode
from salticam.slotmode.image import SlotBackground

from obstools.modelling.core import *  # star imports
from obstools.fastfits import FitsCube
from obstools.modelling.bg import Poly2D
from obstools.modelling.psf.models_lm import EllipticalGaussianPSF
from obstools.modelling.psf.models_lm import CircularGaussianPSF  # repeated
from obstools.phot import log
from obstools.phot.proc import TaskExecutor
from obstools.phot.tracking.core import SegmentedImage, SlotModeTracker, \
    check_image_drift  # multiline

from scrawl.imagine import ImageDisplay
"""
