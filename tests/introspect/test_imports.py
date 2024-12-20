# std
import ast
import textwrap as txw
from pathlib import Path

# third-party
from loguru import logger

# local
from recipes.testing import ECHO, Expected, Warns, expected, mock
from recipes.introspect.imports import (
    ImportCapture, ImportFilter, ImportMerger, ImportRelativizer,
    ImportSplitter, NodeTypeFilter, Parentage, refactor, rewrite)


logger.enable('recipes.introspect')
logger.enable('recipes.introspect.imports')


TESTPATH = Path(__file__).parent.absolute()
EXAMPLES = TESTPATH / 'import_refactor_examples'
# ---------------------------------------------------------------------------- #


def dedent(string):
    return txw.dedent(string).strip()


def parse(code, kls=ast.NodeTransformer, *args, **kws):
    transformer = kls(*args, **kws)
    module = transformer.visit(ast.parse(dedent(code)))
    return transformer, module


def check_parents(node):
    for child in ast.iter_child_nodes(node):
        assert ((child.parent is node) or
                ((child.parent is node.parent) and isinstance(child, ast.Load)))
        check_parents(child)


@expected(
    # All nodes generated by `Parentage` subclasses should have parent attribute
    Parentage.__subclasses__(),
    code='''
        from pyxides.vectorize import CallMapper
        import re
        import operator as op
        import warnings as wrn

        wrn.warn('Dinosaurs!!')
        '''
)
def test_parentage(kls, code, expected):
    _, module = parse(code, kls)

    assert module.parent is None
    check_parents(module)


class TestNodeTransformer:
    Transformer = ast.NodeVisitor  # null transformer

    def parse(self, code, *args, **kws):
        return parse(code, self.Transformer, *args, **kws)


class TestNodeTypeFilter(TestNodeTransformer):
    Transformer = NodeTypeFilter

    @expected({
        ('''
        import re, os
        import operator as op

        op.eq(re, os)
        assert 1 + 1 == 2
        raise SytemExit('Done')
        ''', (ast.Module, ast.Import, ast.ImportFrom, ast.alias)):
        '''
        import re, os
        import operator as op
        '''
    })
    def test_(self, code, keep, expected):
        _, module = self.parse(code, (), keep)
        new = '\n'.join(map(rewrite, module.body))
        assert new == dedent(expected)


class TestImportCapture(TestNodeTransformer):
    Transformer = ImportCapture

    @expected({
        # case: detect names basic
        '''
        from xx.yy import zz
        import re, os
        import operator as op
        ''':  # expected: (imported, used)
        ({'re', 'os', 'op', 'zz'}, set()),

        # case: detect name use as an attribute
        '''
        import logging
        import logging.config

        logging.config.dictConfig({})
        ''':  # expected
        ({'logging', 'logging.config'}, {'logging', 'logging.config'}),

        # case: detect decorator usage
        '''
        from foo import bar

        @bar
        def _():
            pass
        ''':  # expected
        ({'bar'}, {'bar'})
    })
    def test_capture(self, code, expected):
        cap, module = self.parse(code)
        toplevel = cap.imported_names[module]
        used_names = set().union(*cap.used_names.values())

        assert toplevel == expected[0]
        assert used_names == expected[1]

    def test_capture_local(self):
        cap, module = self.parse('''
            def _():
                from foo import bar
                bar()
            ''')
        funcdef = module.body[0]
        assert cap.imported_names[funcdef] == {'bar'}
        assert cap.used_names.popitem()[1] == {'bar'}


class TestImportFilter(TestNodeTransformer):
    Transformer = ImportFilter

    code0 = '''
            from xx.yy import zz
            import re, os
            import operator as op
            '''

    @expected({
        mock(code0, remove=['zz']):
        dedent('''
               import re, os
               import operator as op
               '''),

        mock(code0, remove=['zz', 're']):
        dedent('''
               import os
               import operator as op
               '''),

        mock(code0, remove=['op']):
        dedent('''
               from xx.yy import zz
               import re, os
               import operator
               '''),

        mock('from xx.yy.zz import pp, rr, qq as ww', remove=['qq']):
        'from xx.yy.zz import pp, rr',

        mock('from xx.yy.zz import pp, rr, qq as ww', remove=['ww', 'pp']):
        'from xx.yy.zz import rr, qq',

        mock('from xx.yy import zz as qq, qq as pp', remove=['qq']):
        'from xx.yy import zz',
    })
    def test_filter_alias(self, code, remove, expected):
        _, module = self.parse(code, remove)
        new = '\n'.join(map(rewrite, module.body))
        assert new == expected


class TestImportMerger(TestNodeTransformer):
    Transformer = ImportMerger

    @expected({
        '''
        import numpy as np
        import numpy as np
        ''':
            'import numpy as np',
        '''
        from some.deep.thoughts import brainpower
        from some.deep.thoughts import brainpower
        ''':
            'from some.deep.thoughts import brainpower',
        '''
        from matplotlib.collections import LineCollection
        from matplotlib.collections import EllipseCollection
        ''':
            'from matplotlib.collections import LineCollection, EllipseCollection',
        #
        '''
        from xx.yy import zz as qq
        from xx.yy import ww
        ''':
            'from xx.yy import zz as qq, ww',
        #
        '''
        from xx.yy import zz as qq
        from xx.yy import qq as rr
        ''':
            'from xx.yy import zz as qq, qq as rr',
        #
        '''
        from .. import Campaign
        from .. import HDU
        from .calibrate import calibrate
        from . import logs, WELCOME_BANNER
        from . import FolderTree
        ''':
            '''
            from .. import Campaign, HDU
            from .calibrate import calibrate
            from . import logs, WELCOME_BANNER, FolderTree
            ''',

        '''
        from .. import api
        from .. import cosort, op, pprint as pp
        ''':
            'from .. import api, cosort, op, pprint as pp'
    })
    def test_merge(self, code, expected):
        _, module = self.parse(code)
        assert dedent(expected) == '\n'.join(map(rewrite, module.body))


class TestImportSplitter(TestNodeTransformer):
    Transformer = ImportSplitter

    case1 = '''
    import os, re, this
    from xx import yy as uu, zz as vv
    '''
    
    case2 = '''
    import sys, itertools as itt
    from collections import defaultdict, deque
    '''

    @expected({
        # package / builtin level split
        mock(code=case1, level=0):
            '''
            import os
            import re
            import this
            from xx import yy as uu, zz as vv
            ''',
        # (sub)module level split
        mock(code=case1, level=1):
            '''
            import os, re, this
            from xx import yy as uu
            from xx import zz as vv
            ''',

        mock(code=case1, level=(0, 1)):
            '''
            import os
            import re
            import this
            from xx import yy as uu
            from xx import zz as vv
            ''',
        #
        mock(code=case2, level=0):
            '''
            import sys
            import itertools as itt
            from collections import defaultdict, deque
            '''
    })
    def test_split(self, code, level, expected):
        _, module = self.parse(code, level=level)
        new = '\n'.join(map(rewrite, module.body))
        assert new == dedent(expected)

    # def test_split2(self):
    #     _, module = self.parse('import ast, warnings')
    #     new = '\n'.join(map(rewrite, module.body))
    #     assert new == 'import ast\nimport warnings'


class TestImportRelativizer(TestNodeTransformer):
    Transformer = ImportRelativizer

    @expected({
        # basic
        ('from xx import yy as uu, zz as vv\n'
         'from xx.yy import qq',
         'xx'):
        ('from . import yy as uu, zz as vv\n'
         'from .yy import qq'),

        # one level deep
        (dedent('''
        from recipes import cosort, op
        from recipes.io import open_any
        from recipes import pprint as pp
        from recipes.functionals import negate
        from recipes.string import replace_prefix, truncate
        from recipes.logging import logging, get_module_logger
        from ..io import safe_write
        '''), 'recipes'):
            '''
            from . import cosort, op
            from .io import open_any
            from . import pprint as pp
            from .functionals import negate
            from .string import replace_prefix, truncate
            from .logging import logging, get_module_logger
            from ..io import safe_write
            ''',
        # deeper relativity
        (dedent('''
        from recipes import cosort, op
        from recipes.io import open_any
        from recipes import pprint as pp
        from recipes.functionals import negate
        from recipes.string import replace_prefix, truncate
        from recipes.logging import logging, get_module_logger
        from ..io import safe_write
        '''), 'recipes.other'):
            '''
            from .. import cosort, op
            from ..io import open_any
            from .. import pprint as pp
            from ..functionals import negate
            from ..string import replace_prefix, truncate
            from ..logging import logging, get_module_logger
            from ..io import safe_write
            ''',

        # deeper still: inside a/b/c/d.py
        (dedent('''
        from a import b
        from a.b import c
        from a.b.c import e
        from ...b import f
        from ...b.c import g
        from ..c import h
        from ..c.x import i
        from .c import j        # implies the existence of c/c.py
        '''),
         'a.b.c'):
            '''
            from ... import b
            from .. import c
            from . import e
            from .. import f
            from . import g
            from . import h
            from .x import i
            from .c import j
            ''',

        # modules shadowing builtin names
        (dedent('''
        from recipes.pprint.nrs import xx
        from recipes.string import yy
        '''),
         'recipes.other'):
            '''
            from ..pprint.nrs import xx
            from ..string import yy
            ''',

        # modules shadowing builtin names
        (dedent('''
        from .image import SkyImage, ImageContainer
        from .mosaic import MosaicPlotter
        from .segmentation import SegmentedImage
        '''),
         'recipes.image'):
        # FIXME: ECHO
            '''
            from .image import SkyImage, ImageContainer
            from .mosaic import MosaicPlotter
            from .segmentation import SegmentedImage
            '''
    })
    def test_rename(self, code, old_name, expected):
        _, module = self.parse(code, old_name)
        new = '\n'.join(map(rewrite, module.body))
        assert new == dedent(expected)


test_refactor = Expected(refactor, right_transform=dedent)({
    # case: Warn if asked to filter unused and no code in body (besides imports)
    mock('import this', filter_unused=True):            Warns(),
    #
    mock(dedent('''
        import logging
        import logging.config

        logging.config.dictConfig({})
        '''),
         filter_unused=True, merge=False):                           ECHO,

    # case
    mock(dedent('''
        from recipes.oo import SelfAware, meta

        class X(SelfAware): pass
        '''),
         filter_unused=True):
    '''
    from recipes.oo import SelfAware

    class X(SelfAware): pass
    ''',

    # Test line wrapping
    mock(dedent('''
        from motley.profiler.imports import ImportFinder, ModuleExtractor, \
            ImportExtractor
        ''')):
    '''
    from motley.profiler.imports import (ImportExtractor, ImportFinder,
                                         ModuleExtractor)
    ''',

    #
    mock(dedent('''
        from motley.profiler.imports import ImportFinder, \
            ImportExtractor
        ''')):
    '''
    from motley.profiler.imports import ImportExtractor, ImportFinder
    ''',

    # Test relativize and merge
    mock(dedent('''
        from recipes import cosort, op
        from recipes.io import open_any
        from recipes import pprint as pp
        from recipes.functionals import negate
        from recipes.string import replace_prefix, truncate
        from recipes.logging import logging, get_module_logger
        from .io import safe_write
        '''),
         relativize='recipes'):
        '''
        from . import cosort, op, pprint as pp
        from .functionals import negate
        from .io import open_any, safe_write
        from .string import replace_prefix, truncate
        from .logging import get_module_logger, logging
        ''',
    mock(dedent('''
        from recipes import cosort, op
        from recipes.io import open_any
        from recipes import pprint as pp
        from recipes.functionals import negate
        from recipes.string import replace_prefix, truncate
        from recipes.logging import logging, get_module_logger
        from ..io import safe_write
        '''),
         relativize='recipes.whatever'):
        '''
        from .. import cosort, op, pprint as pp
        from ..functionals import negate
        from ..io import open_any, safe_write
        from ..string import replace_prefix, truncate
        from ..logging import get_module_logger, logging
        ''',

    mock(dedent('''
        from .. import ansi, codes, formatters
        from .xlsx import XlsxWriter
        from .column import resolve_column
        from ..utils import resolve_alignment
        from .utils import *
        from ..formatter import stylize
        '''),
         relativize='motley.table.table'):
        '''
        from .. import ansi, codes, formatters
        from ..formatter import stylize
        from ..utils import resolve_alignment
        from .utils import *
        from .xlsx import XlsxWriter
        from .column import resolve_column
        ''',

    mock(dedent('''
        from recipes import api
        from recipes import api
        from .. import cosort, op, pprint as pp
        from ..iter import unduplicate
        from ..dicts import AttrReadItem
        from ..functionals import negate
        from ..logging import LoggingMixin
        from ..pprint.callers import describe
        from ..string import remove_prefix, truncate
        from ..io import open_any, read_lines, safe_write
        from .utils import BUILTIN_MODULE_NAMES, get_module_name
        '''),
         relativize='recipes.pprint'):
        '''
        from .. import api, cosort, op, pprint as pp
        from ..iter import unduplicate
        from ..dicts import AttrReadItem
        from ..functionals import negate
        from ..logging import LoggingMixin
        from ..string import remove_prefix, truncate
        from ..io import open_any, read_lines, safe_write
        from .callers import describe
        from .utils import BUILTIN_MODULE_NAMES, get_module_name
        '''
})


def rewrite_multiline(code, **kws):
    _, module = parse(code)
    return rewrite(module.body[0], **kws)


test_rewrite = Expected(
    rewrite_multiline,
    code='''
        from recipes.introspect.imports import (Parentage, refactor, 
                                    rewrite,
                                    ImportCapture,
                                    ImportFilter, NodeTypeFilter,
                                    ImportRefactory,
                                    ImportMerger,
                                    rewrite, get_mod_name,
                                    tidy,
                                    ImportSplitter,
                                    Parentage,
                                    ImportRelativizer)
        ''',
    right_transform=dedent
)({
    mock(hang=True):
    '''
            from recipes.introspect.imports import (
                Parentage, refactor, rewrite, ImportCapture, ImportFilter, NodeTypeFilter,
                ImportRefactory, ImportMerger, get_mod_name, tidy, ImportSplitter,
                ImportRelativizer)
            ''',

    mock(hang=False):
    '''
            from recipes.introspect.imports import (Parentage, refactor, rewrite,
                                                    ImportCapture, ImportFilter,
                                                    NodeTypeFilter, ImportRefactory,
                                                    ImportMerger, get_mod_name, tidy,
                                                    ImportSplitter, ImportRelativizer)
            ''',

    mock(hang=False, one_per_line=True):
    '''
            from recipes.introspect.imports import (Parentage,
                                                    refactor,
                                                    rewrite,
                                                    ImportCapture,
                                                    ImportFilter,
                                                    NodeTypeFilter,
                                                    ImportRefactory,
                                                    ImportMerger,
                                                    get_mod_name,
                                                    tidy,
                                                    ImportSplitter,
                                                    ImportRelativizer)
            ''',

    mock(hang=True, one_per_line=True):
    '''
            from recipes.introspect.imports import (
                Parentage,
                refactor,
                rewrite,
                ImportCapture,
                ImportFilter,
                NodeTypeFilter,
                ImportRefactory,
                ImportMerger,
                get_mod_name,
                tidy,
                ImportSplitter,
                ImportRelativizer)
            '''
})


# def test_

# class Test_reformat:

#     @expected(
#         ,
#         cases={

#         })
#     def test_rewrite_multiline(self, code, hang, one_per_line, expected):
#         _, module = parse(code)
#         assert rewrite(module.body[0], 80, hang, 4, one_per_line) == dedent(expected)


# test_relative_imports = Expected(tidy_dedent, right_transform=dedent)({
#     mock(dedent('''
#         from .. import Campaign, HDU
#         from .calibrate import calibrate
#         from . import logs, WELCOME_BANNER
#         from . import FolderTree
#         '''), filter_unused=False):
#         '''
#         from .calibrate import calibrate
#         from .. import shocCampaign, shocHDU
#         from . import logs, WELCOME_BANNER, FolderTree
#         '''
# })

# test_preserve_scope = Expected(
#     tidy_dedent, right_transform=dedent, dedent=dedent('''
#         def _():
#             from foo import bar
#             bar()
#         ''')
# )({mock(unscope=False): ECHO,
#    mock(unscope=True): '''
#             from foo import bar


#             def _():
#                 bar()
#     '''})


# def test_preserve_scope():
#     # unscope=False
#     code = dedent('''
#         def _():
#             from foo import bar
#             bar()
#         ''')
#     assert code == tidy_dedent(code, unscope=False)

#     # unscope=True
#     code = dedent('''
#     from foo import bar


#     def _():
#         bar()
#     ''')
#     assert code == tidy_dedent(code, unscope=True)


# def test_capture_line_limit():
#     imp = ImportRefactory(filter_unused=False)
#     imp.visit(ast.parse(code))


# TODO:
#  test_transform_relative
#  test_make_groups
#  test_sort_aesthetic
#  test_sort_alphabetic
#  test_keep_comments
#  test_style_preference

# @fixture(scope='module')
# def example_file(self):


@expected(
    dict(zip(EXAMPLES.glob('example*.py'),
             EXAMPLES.glob('result*.py'))),
    right_transform=Path.read_text
)
def refactor_file(filename):
    return refactor(filename.read_text())


'''
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

from scrawl.image import ImageDisplay
'''
