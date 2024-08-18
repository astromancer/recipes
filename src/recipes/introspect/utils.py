"""
Introspction utilities.
"""

# std
import re
import io
import os
import sys
import ast
import pkgutil
import inspect
import functools as ftl
import contextlib as ctx
from pathlib import Path
from typing import Union, cast
from types import FrameType, MethodType

# third-party
from stdlib_list import stdlib_list

# relative
from ..string import remove_suffix, truncate


# ---------------------------------------------------------------------------- #
# list of builtin modules
BUILTIN_MODULE_NAMES = [  # TODO: generate at install time for version
    # builtins
    *stdlib_list('.'.join(sys.version.split('.', 2)[:2])),
    # python easter eggs
    'this', 'antigravity'
    # auto-generated module for builtin keywords
    'keyword'
]


# Regex to detect executable python script from source text
REGEX_MAIN_SCRIPT = re.compile(r'if __name__\s*[=!]=\s*__main__')


# maximal filename size. Helps distinguish source code strings from filenames
F_NAMEMAX = os.statvfs('.').f_namemax


# ---------------------------------------------------------------------------- #
#
def is_script(source: str):
    """Detect executable python script from source text."""
    return source.startswith('#!') or REGEX_MAIN_SCRIPT.search(source)


# ---------------------------------------------------------------------------- #

def get_stream(file_or_source):

    if isinstance(file_or_source, io.IOBase):
        return file_or_source

    if isinstance(file_or_source, str):
        if len(file_or_source) < F_NAMEMAX and Path(file_or_source).exists():
            return file_or_source

        # assume string is raw source code
        return io.StringIO(file_or_source)

    if isinstance(file_or_source, Path):
        if file_or_source.exists():
            return file_or_source

        raise FileNotFoundError(f'{truncate(file_or_source, 100)}')

    raise TypeError(
        f'Cannot interpret {type(file_or_source)} as file-like object.'
    )

# ---------------------------------------------------------------------------- #


def get_caller_name(back=1):
    """
    Return the calling function or module name.
    """
    # Adapted from: https://stackoverflow.com/a/57712700/

    frame = get_caller_frame(back + 1)
    try:
        name = frame.f_code.co_name
        return get_module_name(frame) if (name == '<module>') else name
    finally:
        # break reference cycles
        # https://docs.python.org/3/library/inspect.html?highlight=signature#the-interpreter-stack
        del frame


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


# ---------------------------------------------------------------------------- #

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


def get_defining_class(method: MethodType):
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


# ---------------------------------------------------------------------------- #
# Dispatcher for getting module name from import node or path

def get_module_name(obj=None, depth=None):
    """
    Get full (or partial) qualified (dot-separated) name of an object's parent
    (sub)modules and/or package, up to namespace depth `depth`.
    """

    if depth == 0:
        return ''

    # called without arguments => get current module name by inspecting the call
    # stack
    if obj is None:
        obj = get_caller_frame(2)

    # dispatch
    name = _get_module_name(obj)

    if (name == 'builtins') and (depth is None):
        return ''

    if depth in (-1, None):
        depth = 0

    if name:
        return '.'.join(name.split('.')[-depth:])

# @ftl.singledispatch
# def get_module_name(node):
#     """Get the full (dot separated) module name from various types."""
#     raise TypeError(
#         f'No default dispatch method for type {type(node).__name__!r}.'
#     )


@ftl.singledispatch  # generic type implementation
def _get_module_name(obj):

    module = inspect.getmodule(obj)
    if module is None:
        raise TypeError(
            f'Could not determine module for object {obj} of type {type(obj)}.'
        )

    name = module.__name__

    if name == '__main__':
        # if module has no '__file__' attribute, we are either
        # i)  running file as a script
        # ii) in an interactive session
        if not hasattr(module, '__file__'):
            return '__main__'

        #
        name = _get_module_name(module.__file__)

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

    return name


# @_get_module_name.register(type(None))
# # called without arguments => get current module name
# def _(obj):
#     obj = get_caller_frame(4)
#     return get_module_name(obj, depth)


@_get_module_name.register(ast.Import)
def _(node):
    # assert len(node.names) == 1
    return node.names[0].name


@_get_module_name.register(ast.ImportFrom)
def _(node):
    return f'{"." * node.level}{node.module or ""}'


@_get_module_name.register(str)
@_get_module_name.register(Path)
def _(path):
    # get full module name from path
    path = Path(path)
    candidates = []
    trial = path.parent
    stop = (Path.home(), Path('/'), 'src')
    for _ in range(5):
        if trial in stop:
            break

        with ctx.suppress(ImportError):
            if pkgutil.get_loader(trial.name):
                candidates.append(trial)
        trial = trial.parent

    # This next bit is needed since a module may have the same name as a builtin
    # module, eg: "recipes.string". Here "string" would be incorrectly
    # identified here as a "package" since it is importable. The real package
    # may actually be higher up in the folder tree.

    while candidates:
        trial = candidates.pop(-1)
        if candidates and (trial.name in BUILTIN_MODULE_NAMES):
            # candidates.append(trial)
            continue

        # convert to dot.separated.name
        rpath = path.relative_to(trial.parent)
        name = remove_suffix(remove_suffix(str(rpath), '.py'), '__init__')
        if 'src' in name:
            name = name[(name.index('src') + 4):]

        return name.rstrip('/').replace('/', '.')

    raise ValueError(f"Could not get package name for file '{path!s}'.")


def get_package_name(node_or_path: Union[str, Path, ast.Import]):
    fullname = get_module_name(node_or_path)

    # if fullname.startswith('.'):
    #     return '.' * node.level
    if fullname is None:
        raise ValueError(f'Could not get package name for file {node_or_path!r}.')

    # if 'src' in fullname:
    #     from IPython import embed
    #     embed(header="Embedded interpreter at 'src/recipes/introspect/utils.py':312")

    return fullname.split('.', 1)[0]
