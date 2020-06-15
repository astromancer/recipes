def is_interactive():
    """
    True if we are in a notebook / qtconsole
    """
    try:
        return bool(get_ipython())  # .config # True if notebook / qtconsole
    except NameError:
        return False


def exit_register(func, *args, **kws):
    """
    Decorator that registers at post_execute. After its execution it
    unregisters itself for subsequent runs.
    """
    # exit_register runs at the end of ipython %run or the end of the python
    # interpreter.
    # see:
    # http://stackoverflow.com/questions/40186622/atexit-alternative-for-ipython

    if is_interactive():
        ip = get_ipython()

        def callback():
            func(*args, **kws)
            ip.events.unregister('post_execute', callback)

        ip.events.register('post_execute', callback)
    else:
        import atexit
        atexit.register(func, *args, **kws)


def in_notebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True  # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False  # Probably standard Python interpreter


def qtshell(variables):
    # DOES NOT WORK...
    import os
    from IPython.lib import guisupport
    from qtconsole.inprocess import QtInProcessKernelManager
    from qtconsole.rich_jupyter_widget import RichJupyterWidget

    def print_process_id():
        print('Process ID is:', os.getpid())

    # Print the ID of the main process
    print_process_id()
    variables['print_process_id'] = print_process_id

    app = guisupport.get_app_qt4()

    # Create an in-process kernel
    # >>> print_process_id()
    # will print the same process ID as the main process
    kernel_manager = QtInProcessKernelManager()
    kernel_manager.start_kernel()
    kernel = kernel_manager.kernel
    kernel.gui = 'qt5'
    kernel.shell.push(variables)

    kernel_client = kernel_manager.client()
    kernel_client.start_channels()

    def stop():
        kernel_client.stop_channels()
        kernel_manager.shutdown_kernel()
        # app.exit()

    control = RichJupyterWidget()
    control.kernel_manager = kernel_manager
    control.kernel_client = kernel_client
    control.exit_requested.connect(stop)
    control.show()

    guisupport.start_event_loop_qt5(app)
