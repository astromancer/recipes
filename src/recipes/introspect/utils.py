"""
Introspction utilities.
"""

# std
import ast
import sys
import pkgutil
import inspect
import contextlib
import functools as ftl
from typing import cast
from pathlib import Path
from warnings import warn
from types import FrameType, MethodType

# third-party
from stdlib_list import stdlib_list

# relative
from ..string import remove_suffix


# list of builtin modules
BUILTIN_MODULE_NAMES = [  # TODO: generate at install time for version
    # builtins
    *stdlib_list(sys.version[:3]),
    # python easter eggs
    'this', 'antigravity'
    # auto-generated module for builtin keywords
    'keyword'
]


def get_caller_frame(back=1):
    frame = cast(FrameType, inspect.currentframe())
    try:
        while back:
            new_frame = cast(FrameType, frame.f_back)
            back -= 1
            del frame
            frame = new_frame
            del new_frame
        return frame
    finally:
        # break reference cycles
        # https://docs.python.org/3/library/inspect.html?highlight=signature#the-interpreter-stack
        del frame


def get_caller_name(back=1):
    """
    Return the calling function or module name.
    """
    # Adapted from: https://stackoverflow.com/a/57712700/

    frame = get_caller_frame(back + 1)
    try:
        name = frame.f_code.co_name
        if name == '<module>':
            return get_module_name(frame)
        return name
    finally:
        # break reference cycles
        # https://docs.python.org/3/library/inspect.html?highlight=signature#the-interpreter-stack
        del frame


# ---------------------------------------------------------------------------- #
# Dispatcher for getting module name import node or path

# @ftl.singledispatch
# def get_module_name(node):  # rename get_qualname
#     """Get the full (dot separated) module name from various types."""
#     raise TypeError(
#         f'No default dispatch method for type {type(node).__name__!r}.'
#     )

def get_module_name(obj=None, depth=None):
    # called without arguments => get current module name by inspecting the call
    # stack
    if obj is None:
        obj = get_caller_frame(2)

    return _get_module_name(obj, depth)


@ftl.singledispatch  # generic type implementation
def _get_module_name(obj, depth=None):
    """
    Get full (or partial) qualified (dot-separated) name of an object's parent
    (sub)modules and/or package, up to namespace depth `depth`.
    """

    if depth == 0:
        return ''

    module = inspect.getmodule(obj)
    name = module.__name__

    if name == '__main__':
        from pathlib import Path

        # if module has no '__file__' attribute, we are either
        # i)  running file as a script
        # ii) in an interactive session
        if not hasattr(module, '__file__'):
            return ('' if depth is None else '__main__')

        name = Path(module.__file__).stem

    if (name == 'builtins') and (depth is None):
        return ''

        # return Path(mod.__file__).stem

        # file = getattr(mod, '__file__', None)

        # # step through all system paths to find the package root
        # for path in sys.path:
        #     candidates = []
        #     if path and file.startswith(path):
        #         candidates.append(file.replace(path, '').lstrip('/'))
        #         break
        # else:
        #     # function defined in current script
        #     rpath = file

        # for suf in SUFFIXES:
        #     if rpath.endswith(suf):
        #         rpath = rpath.replace(suf, '')
        #         break
        # else:
        #     raise ValueError

    if depth in (-1, None):
        depth = 0

    return '.'.join(name.split('.')[-depth:])


# @_get_module_name.register(type(None))
# # called without arguments => get current module name
# def _(obj, depth=None):
#     obj = get_caller_frame(4)
#     return get_module_name(obj, depth)


@_get_module_name.register(ast.Import)
def _(node, depth=None):
    # assert len(node.names) == 1
    return node.names[0].name


@_get_module_name.register(ast.ImportFrom)
def _(node, depth=None):
    return f'{"." * node.level}{node.module or ""}'


@_get_module_name.register(str)
@_get_module_name.register(Path)
def _(path, depth=None):
    # get full module name from path
    path = Path(path)
    candidates = []
    trial = path.parent
    stop = (Path.home(), Path('/'))
    for _ in range(5):
        if trial in stop:
            break

        with contextlib.suppress(ImportError):
            if pkgutil.get_loader(trial.name):
                candidates.append(trial)
        trial = trial.parent

    # This next bit is needed since a module may have the same name as a builtin
    # module, eg: "recipes.string". Here "string" would be incorrectly
    # identified here as a "package" since it is importable. The real package
    # may actually be higher up in the folder tree.
    while candidates:
        trial = candidates.pop(0)
        if candidates and (trial.name in BUILTIN_MODULE_NAMES):
            # candidates.append(trial)
            continue

        # convert to dot.separated.name
        path = path.relative_to(trial.parent)
        name = remove_suffix(remove_suffix(str(path), '.py'), '__init__')
        return name.rstrip('/').replace('/', '.')

    warn(f"Could not find package name for '{path}'.")


# def get_module_name(filename, depth=1):

#     name = inspect.getmodulename(filename)
#     # for modules that have `__init__.py`
#     if name == '__init__':
#         return '.'.join(filename.split('/')[-depth - 1:-1])

#     # note the following block merely splits the filename.  no checks
#     #  are done to see if the path is actually a valid python module
#     current_depth = name.count('.')
#     if depth > current_depth:
#         parts = filename.split('/')[-depth - 1:-1]
#         parts.append(name)
#         return '.'.join(parts)

#     return name.split('.', name.count('.') - depth)[-1]


def get_class_name(obj, depth=None):
    """
    Get the fully (or partially) qualified (dot-separated) name of an object and
    its parent (sub)modules and/or package.

    Parameters
    ----------
    obj : object
        The object to be named
    depth : int, optional
        Namespace depth, by default None.
        # eg:. foo.sub.Klass #for depth of 2

    Examples
    --------
    >>> 
    """
    kls = obj if isinstance(obj, type) else type(obj)
    return '.'.join((get_module_name(kls, depth), kls.__name__))


def get_class_that_defined_method(method: MethodType):
    """
    Get the class that defined a method.

    Parameters
    ----------
    method : types.MethodType
        The method for which the defining class will be retrieved.

    Returns
    -------
    type
        Class that defined the method.
    """
    # source: https://stackoverflow.com/questions/3589311/#25959545

    # handle bound methods
    if inspect.ismethod(method):
        for cls in inspect.getmro(method.__self__.__class__):
            if cls.__dict__.get(method.__name__) is method:
                return cls
        method = method.__func__  # fallback to __qualname__ parsing

    # handle unbound methods
    if inspect.isfunction(method):
        name = method.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
        cls = getattr(inspect.getmodule(method), name)
        if isinstance(cls, type):
            return cls

    # handle special descriptor objects
    return getattr(method, '__objclass__', None)
