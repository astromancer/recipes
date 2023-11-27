"""
Host of useful miscellaneous classes and functions.
"""


# std
import shutil
from numbers import Number

# third-party
from loguru import logger

# relative
from .interactive import is_interactive


ZERO_DEPTH_BASES = (str, bytes, Number, range, bytearray)


def get_size(fallback=(80, 24)):
    """Returns the initial terminal size."""

    # NOTE: NOT DYNAMIC. ie. resizing a window voids this ?
    # FIXME:

    if not is_interactive():
        return shutil.get_terminal_size(fallback)

    # in notebook / qtconsole / ipython terminal
    # NOTE: AFAICT it's not possible to distinguish between qtconsole and
    # notebook here

    from jupyter_core.paths import jupyter_config_dir
    from pathlib import Path
    import re

    path = Path(jupyter_config_dir())
    config_file = path / 'jupyter_qtconsole_config.py'

    wh = []
    with config_file.open() as fp:
        raw = fp.read()
        for j, s in enumerate(('width', 'height')):
            if mo := re.search(rf'c.ConsoleWidget.console_{s} = (\d+)', raw):
                w_h = int(mo.group(1))
            else:
                # fallback
                logger.warning('Cannot determine terminal size for this '
                               'interactive session')
                w_h = fallback[j]
            wh.append(w_h)

    w, h = wh
    return w, h


