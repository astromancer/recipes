import shutil, tempfile
from recipes.testing import expected, mock
from recipes.string.restring import (RGX_PYSTRING, RGX_PRINTF_STR,
                                     _convert_fstring, strip_trailing_space)

import pytest


# @pytest.mark.parametrize('s',
#                          {'%  s',
#                           '% F',
#                           '% a',
#                           '% c',
#                           '% d',
#                           '% e',
#                           '% f',
#                           '% g',
#                           '% i',
#                           '% o',
#                           '% r',
#                           '% s',
#                           '% u',
#                           '% x',
#                           '%%',
#                           '%(P)s',
#                           '%(asctime)s',
#                           '%(ge)s',
#                           '%(gj)s',
#                           '%(levelname)-8s',
#                           '%(message)s',
#                           '%(name)-15s',
#                           '%(processName)-10s',
#                           '%(prog)s',
#                           '%*s',
#                           '%+3.2f',
#                           '%+g',
#                           '%-10s',
#                           '%-12.6f',
#                           '%-12.9f',
#                           '%-15s',
#                           '%-18.9f',
#                           '%-18s',
#                           '%-20s',
#                           '%-23s',
#                           '%-25s',
#                           '%-2i',
#                           '%-2s',
#                           '%-35s',
#                           '%-38s',
#                           '%-3s',
#                           '%-9.3f',
#                           '%-9.6f',
#                           '%-s',
#                           '%.0f',
#                           '%.100r',
#                           '%.10f',
#                           '%.1f',
#                           '%.2f',
#                           '%.3d',
#                           '%.3f',
#                           '%.4g',
#                           '%.5f',
#                           '%.X',
#                           '%1.1f',
#                           '%1.2f',
#                           '%1.3f',
#                           '%1.3g',
#                           '%1.4f',
#                           '%12.3f',
#                           '%18.9f',
#                           '%2.4f',
#                           '%2.5f',
#                           '%20i',
#                           '%27s',
#                           '%28d',
#                           '%3.1f',
#                           '%3.2f',
#                           '%3.4f',
#                           '%3c',
#                           '%3i',
#                           '%5.2f',
#                           '%5.3f',
#                           '%7.3f',
#                           '%7.5f',
#                           '%80%',
#                           '%9.5f',
#                           '%E',
#                           '%F',
#                           '%G',
#                           '%X',
#                           '%a',
#                           '%c',
#                           '%d',
#                           '%f',
#                           '%g',
#                           '%i',
#                           '%o',
#                           '%r',
#                           '%s',
#                           '%u',
#                           '%x',
#                           '%3.*f'}
#                          )
# def test_find_printf(s):
#     RGX_PRINTF_STR.search(s)


# EXAMPLES = '_refactor_examples_pre.py'


@expected(
    {"""raise ValueError('Arithmetic on %s objects with different '
                         'sizes not permitted' % self.__class__)""":
        "f'Arithmetic on {self.__class__} objects with '\n"
        "                         f'different sizes not permitted'",
    #  """
    #  raise TooManyToPlot(
    #     'Received %i time series to plot. This is probably not what you wanted. Refusing since safety limit '
    #     'is currently set to %i to avoid accidental compute intensive '
    #     'commands from overwhelming system resources.'
    #     % (n, N_MAX_TS_SAFETY))
    #     """: 
        
     }
)
def test_convert_fstring():
    _convert_fstring('refactor_examples_pre.py', 8)

from pathlib import Path

def test_strip_trailing_spaces():
    fd, name = tempfile.mkstemp()
    shutil.copy('_trailing_space.py', name)
    strip_trailing_space(name)
    new = Path(name).read_text()
    ref = Path('trailing_space.py').read_text()