"""
Context manager that aids setting temporary attribute value(s) and restores
previous value(s) at exit context.
"""

# std
import contextlib as ctx

# third-party
from loguru import logger


@ctx.contextmanager
def temporarily(obj, **kws):
    """Temporarily set attribute value(s). Restore previous value(s) at exit."""

    original = {atr: getattr(obj, atr) for atr in kws}
    try:
        for atr, val in kws.items():
            logger.debug('Setting attribute values for context: {} = {!r}.',
                         atr, val)
            setattr(obj, atr, val)
        yield obj
    except:
        raise
    finally:
        for atr, val in original.items():
            logger.debug('Restoring original attribute value at context exit: '
                         '{!r}: {} -> {}', atr, getattr(obj, atr), val)
            setattr(obj, atr, val)


temporary = temporarily
