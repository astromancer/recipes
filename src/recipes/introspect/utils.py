import inspect
from types import FrameType
from typing import cast


# from importlib.machinery import all_suffixes
# SUFFIXES = all_suffixes()


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
    Return the calling function or module name
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


def get_module_name(obj=None, depth=None):
    #
    if obj is None:
        obj = get_caller_frame(2)

    if depth == 0:
        return ''

    mod = inspect.getmodule(obj)
    name = mod.__name__

    if name == '__main__':
        from pathlib import Path

        # if mod has no '__file__' attribute, we are either
        # i)  running file as a script
        # ii) in an interactive session
        if not hasattr(mod, '__file__'):
            if depth is None:
                return ''
            return '__main__'

        name = Path(mod.__file__).stem

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


def get_class_that_defined_method(method):
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
