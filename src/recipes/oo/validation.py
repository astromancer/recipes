from pydantic import TypeAdapter, ValidationError
from typing import Any
import contextlib as ctx

# type_def: type|TypeAlias

def compound_isinstance(obj: Any, type_def: type) -> bool:
    """
    Check if an object matches a given type definition using pydantic's
    validation system. This serves as a drop in replacement for `isinstance`
    that can handle compound type definitions.

    Parameters
    ----------
    obj : object
        The object to be checked.
    type_def : type or TypeAlias
        Type definition to check against. Can be a builtin type or a TypeAlias
        defined using pythons typing mechanisms.
    Examples
    --------
    >>> compound_isinstance(("1", 2), Sequence[str, int])
    True
    >>> compound_isinstance(("1", 2), int)
    False

    Returns
    -------
    bool
        True if `obj` matches the `type_def`, False otherwise.
    """

    with ctx.suppress(ValidationError):
        TypeAdapter(type_def).validate_python(obj)
        return True

    return False
