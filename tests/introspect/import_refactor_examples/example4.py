# std
import logging
import functools as ftl
import itertools as itt
import multiprocessing as mp
import tempfile
from pathlib import Path

# third-party
import numpy as np
import more_itertools as mit
from sklearn.cluster import MeanShift
from scipy.spatial.distance import cdist
from astropy.utils import lazyproperty
from astropy.stats import median_absolute_deviation as mad

# local
from obstools.image.registration import compute_centres_offsets, \
    group_features, report_measurements  # register
from recipes.dicts import AttrReadItem
from recipes.logging import get_module_logger, LoggingMixin
from recipes.parallel.synced import SyncedCounter, SyncedArray
from obstools.image.segmentation import SegmentedImage, SegmentsModelHelper, \
    LabelGroupsMixin, merge_segmentations, select_rect_pad
from obstools.image.detect import make_border_mask
from obstools.io import load_memmap
from graphing.imagine import ImageDisplay
from matplotlib.transforms import AffineDeltaTransform

from obstools.image.registration import ImageRegister
