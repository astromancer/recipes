import contextlib as ctx


@ctx.contextmanager
def temporarily(obj, **kws):
    """Temporarily set attribute value(s)."""
    
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