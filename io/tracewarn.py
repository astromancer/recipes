import warnings
import traceback

__all__ = ['warn_with_traceback', 'warning_traceback_on', 'warning_traceback_off']

# setup warnings to print full traceback
original_formatwarning = warnings.formatwarning  # backup original warning formatter


def warn_with_traceback(*args, **kwargs):
    s = original_formatwarning(*args, **kwargs)
    tb = traceback.format_stack()
    s += ''.join(tb[:-1])
    return s


def warning_traceback_on():
    warnings.formatwarning = warn_with_traceback

def warning_traceback_off():
    warnings.formatwarning = original_formatwarning




