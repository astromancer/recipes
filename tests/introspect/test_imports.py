# std
import ast
from pathlib import Path
from textwrap import dedent

# local
from recipes.string import remove_prefix
from recipes.testing import Expected, expected, mock, ECHO, Warns
from recipes.introspect.imports import (Parentage, refactor, rewrite,
                                        ImportCapture,
                                        ImportFilter, NodeTypeFilter,
                                        ImportRefactory,
                                        ImportMerger,
                                        rewrite,
                                        tidy,
                                        ImportSplitter,
                                        Parentage,
                                        ImportRelativizer)

TESTPATH = Path(__file__).parent.absolute()
EXAMPLES = TESTPATH / 'import_refactor_examples'
# ---------------------------------------------------------------------------- #


def source(string):
    return dedent(string).strip()


def parse(kls, code, *args, **kws):
    transformer = kls(*args, **kws)
    module = transformer.visit(ast.parse(source(code)))
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
        from pyxides.vectorize import MethodVectorizer
        import re
        import operator as op
        import warnings as wrn

        wrn.warn('Dinosaurs!!')
        '''
)
def test_parentage(kls, code, expected):
    _, module = parse(kls, code)

    assert module.parent is None
    check_parents(module)


class TestNodeTransformer:
    def parse(self, code, *args, **kws):
        Transformer = eval(remove_prefix(type(self).__name__, 'Test'))
        return parse(Transformer, code, *args, **kws)


class TestNodeTypeFilter(TestNodeTransformer):
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
        assert new == source(expected)


class TestImportCapture(TestNodeTransformer):

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

    code0 = '''
            from xx.yy import zz
            import re, os
            import operator as op
            '''

    @expected({
        mock(code0, remove=['zz']):
        source('''
                import re, os
                import operator as op
            '''),

        mock(code0, remove=['zz', 're']):
        source('''
                import os
                import operator as op
            '''),

        mock(code0, remove=['op']):
        source('''
                from xx.yy import zz
                import re, os
            '''),

        mock('from xx.yy.zz import pp, rr, qq as ww', remove=['ww', 'pp']):
        'from xx.yy.zz import rr',

        mock('from xx.yy import zz as qq, qq as pp', remove=['qq']):
        'from xx.yy import qq as pp',
    })
    def test_filter_alias(self, code, remove, expected):
        _, module = self.parse(code, remove)
        new = '\n'.join(map(rewrite, module.body))
        assert new == expected


class TestImportMerger(TestNodeTransformer):

    @expected({
        '''
        from matplotlib.collections import LineCollection
        from matplotlib.collections import EllipseCollection
        ''':
        "from matplotlib.collections import LineCollection, EllipseCollection",
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
        from .. import shocCampaign
        from .. import shocHDU
        from .calibrate import calibrate
        from . import logs, WELCOME_BANNER
        from . import FolderTree
        ''':
        '''
        from .. import shocCampaign, shocHDU
        from .calibrate import calibrate
        from . import logs, WELCOME_BANNER, FolderTree
        '''
    })
    def test_merge(self, code, expected):
        _, module = self.parse(code)
        new = '\n'.join(map(rewrite, module.body))
        assert new == source(expected)


class TestImportSplitter(TestNodeTransformer):
    @expected(
        code='''
             import os, re, this
             from xx import yy as uu, zz as vv
             ''',
        cases={
            # package / builtin level split
            mock(level=0):
            '''
            import os
            import re
            import this
            from xx import yy as uu, zz as vv
            ''',
            # (sub)module level split
            mock(level=1):
            '''
            import os, re, this
            from xx import yy as uu
            from xx import zz as vv
            ''',

            mock(level=(0, 1)):
            '''
            import os
            import re
            import this
            from xx import yy as uu
            from xx import zz as vv
            '''
        })
    def test_split(self, code, level, expected):
        _, module = self.parse(code, level=level)
        new = '\n'.join(map(rewrite, module.body))
        assert new == source(expected)


class TestImportRelativizer(TestNodeTransformer):
    @expected({
        # basic
        ('from xx import yy as uu, zz as vv\n'
         'from xx.yy import qq',
         'xx'):
        ('from . import yy as uu, zz as vv\n'
         'from .yy import qq'),

        # one level deep
        (source('''
            from recipes import cosort, op
            from recipes.io import open_any
            from recipes import pprint as pp
            from recipes.functionals import negate
            from recipes.string import replace_prefix, truncate
            from recipes.logging import logging, get_module_logger
            from ..io import safe_write
            '''),
            'recipes'):
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
        (source('''
            from recipes import cosort, op
            from recipes.io import open_any
            from recipes import pprint as pp
            from recipes.functionals import negate
            from recipes.string import replace_prefix, truncate
            from recipes.logging import logging, get_module_logger
            from ..io import safe_write
            '''),
            'recipes.other'):
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
        (source('''
        from a import b
        from a.b import c
        from a.b.c import e
        from ..b import f
        from ..b.c import g
        from .c import h
        '''),
         'a.b.c'):
        '''
        from ... import b
        from .. import c
        from . import e
        from .. import f
        from . import g
        from . import h
        '''
    })
    def test_rename(self, code, old_name, expected):
        _, module = self.parse(code, old_name)
        new = '\n'.join(map(rewrite, module.body))
        assert new == source(expected)


test_refactor = Expected(refactor, right_transform=source)({
    # case: Warn if asked to filter unused and no code in body (besides imports)
    mock('import this', filter_unused=True):            Warns(),
    #
    mock(source('''
            import logging
            import logging.config

            logging.config.dictConfig({})
            '''),
         filter_unused=True):                            ECHO,

    # case
    mock(source('''
        from recipes.oo import SelfAware, meta

        class X(SelfAware): pass
        '''),
         filter_unused=True):
    '''
    from recipes.oo import SelfAware

    class X(SelfAware): pass
    ''',

    # Test line wrapping
    mock(source('''
        from motley.profiler.imports import ImportFinder, ModuleExtractor, \
            ImportExtractor
        ''')):
    '''
    from motley.profiler.imports import (ImportFinder, ModuleExtractor,
                                         ImportExtractor)
    ''',

    #
    mock(source('''
        from motley.profiler.imports import ImportFinder, \
            ImportExtractor
        ''')):
    '''
    from motley.profiler.imports import ImportFinder, ImportExtractor
    ''',

    # Test relativize and merge
    mock(source('''
        from recipes import cosort, op
        from recipes.io import open_any
        from recipes import pprint as pp
        from recipes.functionals import negate
        from recipes.string import replace_prefix, truncate
        from recipes.logging import logging, get_module_logger
        from ..io import safe_write
        '''),
         relativize='recipes'):
        '''
        from . import cosort, op, pprint as pp
        from .functionals import negate
        from .io import open_any, safe_write
        from .string import replace_prefix, truncate
        from .logging import logging, get_module_logger
        ''',
    mock(source('''
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
        from ..logging import logging, get_module_logger
        '''

})


# test_relative_imports = Expected(tidy_source, right_transform=source)({
#     mock(source('''
#         from .. import shocCampaign, shocHDU
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
#     tidy_source, right_transform=source, source=source('''
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
#     code = source('''
#         def _():
#             from foo import bar
#             bar()
#         ''')
#     assert code == tidy_source(code, unscope=False)

#     # unscope=True
#     code = source('''
#     from foo import bar


#     def _():
#         bar()
#     ''')
#     assert code == tidy_source(code, unscope=True)


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

from scrawl.imagine import ImageDisplay
'''
