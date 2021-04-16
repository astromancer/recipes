from recipes.string.restring import RGX_PYSTRING, RGX_PRINTF_STR

import pytest

@pytest.mark.parametrize('s',
{'%  s',
 '% F',
 '% a',
 '% c',
 '% d',
 '% e',
 '% f',
 '% g',
 '% i',
 '% o',
 '% r',
 '% s',
 '% u',
 '% x',
 '%%',
 '%(P)s',
 '%(asctime)s',
 '%(ge)s',
 '%(gj)s',
 '%(levelname)-8s',
 '%(message)s',
 '%(name)-15s',
 '%(processName)-10s',
 '%(prog)s',
 '%*s',
 '%+3.2f',
 '%+g',
 '%-10s',
 '%-12.6f',
 '%-12.9f',
 '%-15s',
 '%-18.9f',
 '%-18s',
 '%-20s',
 '%-23s',
 '%-25s',
 '%-2i',
 '%-2s',
 '%-35s',
 '%-38s',
 '%-3s',
 '%-9.3f',
 '%-9.6f',
 '%-s',
 '%.0f',
 '%.100r',
 '%.10f',
 '%.1f',
 '%.2f',
 '%.3d',
 '%.3f',
 '%.4g',
 '%.5f',
 '%.X',
 '%1.1f',
 '%1.2f',
 '%1.3f',
 '%1.3g',
 '%1.4f',
 '%12.3f',
 '%18.9f',
 '%2.4f',
 '%2.5f',
 '%20i',
 '%27s',
 '%28d',
 '%3.1f',
 '%3.2f',
 '%3.4f',
 '%3c',
 '%3i',
 '%5.2f',
 '%5.3f',
 '%7.3f',
 '%7.5f',
 '%80%',
 '%9.5f',
 '%E',
 '%F',
 '%G',
 '%X',
 '%a',
 '%c',
 '%d',
 '%f',
 '%g',
 '%i',
 '%o',
 '%r',
 '%s',
 '%u',
 '%x',
 '%3.*f'}
)
def test_find_printf(s):
    RGX_PRINTF_STR.search(s)
    
    