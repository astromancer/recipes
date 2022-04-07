"""
Context manager that aids setting temporary attribute value(s) and restores
previous value(s) at exit context.
"""

import contextlib as ctx


@ctx.contextmanager
def temporarily(obj, **kws):
    """Temporarily set attribute value(s). Restore previous value(s) at exit."""
    
    original = {atr: getattr(obj, atr) for atr in kws}
    try:
        for atr, val in kws.items():
            setattr(obj, atr, val)
        yield obj
    except:
        raise
    finally:
        for atr, val in original.items():
            setattr(obj, atr, val)
            
temporary = temporarily