import inspect


def get_module_name(filename, depth=1):
    name = inspect.getmodulename(filename)
    # for modules that have `__init__.py`
    if name == '__init__':
        return '.'.join(filename.split('/')[-depth - 1:-1])

    # note the following block merely splits the filename.  no checks
    #  are done to see if the path is actually a valid python module
    current_depth = name.count('.')
    if depth > current_depth:
        parts = filename.split('/')[-depth - 1:-1]
        parts.append(name)
        return '.'.join(parts)

    return name.split('.', name.count('.') - depth)[-1]


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
