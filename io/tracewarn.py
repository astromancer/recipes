import warnings
import traceback

#TODO: filter ipython stuff from traceback:
#/usr/local/lib/python3.5/dist-packages/matplotlib-2.0.0+4130.g481e860-py3.5-linux-x86_64.egg/mpl_toolkits/mplot3d/axes3d.py:620: UserWarning: Attempting to set identical left==right results
# in singular transformations; automatically expanding.
# left=0, right=0
#   'left=%s, right=%s') % (left, right))
#   File "/usr/lib/python3.5/runpy.py", line 193, in _run_module_as_main
#     "__main__", mod_spec)
#   File "/usr/lib/python3.5/runpy.py", line 85, in _run_code
#     exec(code, run_globals)
#   File "/usr/local/lib/python3.5/dist-packages/ipykernel_launcher.py", line 16, in <module>
#     app.launch_new_instance()
#   File "/home/hannes/.local/lib/python3.5/site-packages/traitlets/config/application.py", line 658, in launch_instance
#     app.start()
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/kernelapp.py", line 474, in start
#     ioloop.IOLoop.instance().start()
#   File "/home/hannes/.local/lib/python3.5/site-packages/zmq/eventloop/ioloop.py", line 177, in start
#     super(ZMQIOLoop, self).start()
#   File "/home/hannes/.local/lib/python3.5/site-packages/tornado/ioloop.py", line 831, in start
#     self._run_callback(callback)
#   File "/home/hannes/.local/lib/python3.5/site-packages/tornado/ioloop.py", line 604, in _run_callback
#     ret = callback()
#   File "/home/hannes/.local/lib/python3.5/site-packages/tornado/stack_context.py", line 275, in null_wrapper
#     return fn(*args, **kwargs)
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/kernelbase.py", line 258, in enter_eventloop
#     self.eventloop(self)
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/eventloops.py", line 93, in loop_qt5
#     return loop_qt4(kernel)
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/eventloops.py", line 87, in loop_qt4
#     start_event_loop_qt4(kernel.app)
#   File "/home/hannes/.local/lib/python3.5/site-packages/IPython/lib/guisupport.py", line 144, in start_event_loop_qt4
#     app.exec_()
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/eventloops.py", line 39, in process_stream_events
#     kernel.do_one_iteration()
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/kernelbase.py", line 291, in do_one_iteration
#     stream.flush(zmq.POLLIN, 1)
#   File "/home/hannes/.local/lib/python3.5/site-packages/zmq/eventloop/zmqstream.py", line 352, in flush
#     self._handle_recv()
#   File "/home/hannes/.local/lib/python3.5/site-packages/zmq/eventloop/zmqstream.py", line 472, in _handle_recv
#     self._run_callback(callback, msg)
#   File "/home/hannes/.local/lib/python3.5/site-packages/zmq/eventloop/zmqstream.py", line 414, in _run_callback
#     callback(*args, **kwargs)
#   File "/home/hannes/.local/lib/python3.5/site-packages/tornado/stack_context.py", line 275, in null_wrapper
#     return fn(*args, **kwargs)
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/kernelbase.py", line 276, in dispatcher
#     return self.dispatch_shell(stream, msg)
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/kernelbase.py", line 228, in dispatch_shell
#     handler(stream, idents, msg)
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/kernelbase.py", line 390, in execute_request
#     user_expressions, allow_stdin)
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/ipkernel.py", line 196, in do_execute
#     res = shell.run_cell(code, store_history=store_history, silent=silent)
#   File "/home/hannes/.local/lib/python3.5/site-packages/ipykernel/zmqshell.py", line 501, in run_cell
#     return super(ZMQInteractiveShell, self).run_cell(*args, **kwargs)
#   File "/home/hannes/.local/lib/python3.5/site-packages/IPython/core/interactiveshell.py", line 2717, in run_cell
#     interactivity=interactivity, compiler=compiler, result=result)
#   File "/home/hannes/.local/lib/python3.5/site-packages/IPython/core/interactiveshell.py", line 2827, in run_ast_nodes
#     if self.run_code(code, result):
#   File "/home/hannes/.local/lib/python3.5/site-packages/IPython/core/interactiveshell.py", line 2881, in run_code
#     exec(code_obj, self.user_global_ns, self.user_ns)
#   File "<ipython-input-73-648e81894661>", line 4, in <module>
#     PSFPlotter(fitsfile, model, coords, window)
#   File "<ipython-input-72-49daab334d5e>", line 9, in __init__
#     Compare3DImage.__init__(self, *self.grid, Z, data)
#   File "/home/hannes/.local/lib/python3.5/site-packages/grafico/imagine.py", line 900, in __init__
#     self.update(*data)
#   File "/home/hannes/.local/lib/python3.5/site-packages/grafico/imagine.py", line 1024, in update
#     ax.set_xlim([X[0, 0], X[0, -1]])
#   File "/usr/local/lib/python3.5/dist-packages/matplotlib-2.0.0+4130.g481e860-py3.5-linux-x86_64.egg/mpl_toolkits/mplot3d/axes3d.py", line 620, in set_xlim3d
#     'left=%s, right=%s') % (left, right))
#   File "/usr/local/lib/python3.5/dist-packages/astropy-2.0.dev17771-py3.5-linux-x86_64.egg/astropy/logger.py", line 175, in _showwarning
#     return self._showwarning_orig(*args, **kwargs)
#   File "/usr/lib/python3.5/warnings.py", line 18, in showwarning
#     file.write(formatwarning(message, category, filename, lineno, line))
# /usr/local/lib/python3.5/dist-packages/matplotlib-2.0.0+4130.g481e860-py3.5-linux-x86_64.egg/mpl_toolkits/mplot3d/axes3d.py:672: UserWarning: Attempting to set identical bottom==top results
# in singular transformations; automatically expanding.
# bottom=0, top=0
#   'bottom=%s, top=%s') % (bottom, top))

__all__ = ['warn_with_traceback', 'warning_traceback_on', 'warning_traceback_off']

# setup warnings to print full traceback
original_formatwarning = warnings.formatwarning  # backup original warning formatter


def warn_with_traceback(*args, **kwargs):
    s = original_formatwarning(*args, **kwargs)
    tb = traceback.format_stack()
    s += ''.join(tb[:-1])
    return s


def warning_traceback_on():
    warnings.formatwarning = warn_with_traceback

def warning_traceback_off():
    warnings.formatwarning = original_formatwarning




