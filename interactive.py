
def is_interactive():
    try:
        return bool(get_ipython().config)        #True if notebook / qtconsole
    except NameError:
        return False

# def is_interactive():
#     import __main__ as main
#     return not hasattr(main, '__file__')


# exit_register runs at the end of ipython %run or the end of the python interpreter
# see: http://stackoverflow.com/questions/40186622/atexit-alternative-for-ipython
def exit_register(fun):
    """
    Decorator that registers at post_execute. After its execution it
    unregisters itself for subsequent runs. 
    """

    if not is_interactive():
        return fun

    ip = get_ipython()

    def callback():
        fun()
        ip.events.unregister('post_execute', callback)

    ip.events.register('post_execute', callback)


def in_notebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter