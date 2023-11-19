
# std
import functools

# third-party
from PyQt5.QtCore import pyqtRemoveInputHook, pyqtRestoreInputHook


def unhookPyQt(func):
    """
    Decorator that removes the PyQt input hook during the execution of the
    decorated function.
    Used for functions that need ipython / terminal input prompts to work with
    pyQt.
    """

    @functools.wraps(func)
    def unhooked_func(*args, **kwargs):
        pyqtRemoveInputHook()
        out = func(*args, **kwargs)
        pyqtRestoreInputHook()
        return out

    return unhooked_func
