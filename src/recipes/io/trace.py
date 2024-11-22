# std
import os
import sys
import warnings
import traceback

# third-party
from warnings import formatwarning as original_formatwarning

# relative
from ..string import overlay

class MessageWrapper:

    def __init__(self, wrapped, title=None, width=80, char='='):
        self.active = True

        if isinstance(wrapped, MessageWrapper):
            # avoid wrapping multiple times !!!
            self.wrapped = wrapped.wrapped
        else:
            self.wrapped = wrapped

        # get the class name and pad with single whitespace on each side
        title = self.get_title(title)
        self.width = int(width)
        self.pre = os.linesep + overlay(title, char * self.width, '^')
        self.post = (char * self.width)

    def __call__(self, *args, **kws):
        return self._wrap_message(self.wrapped(*args, **kws))

    def get_title(self, title):
        if title is None:
            title = self.__class__.__name__
        return title.join('  ')

    def _wrap_message(self, msg):
        if self.active:
            # make banner
            return os.linesep.join((self.pre,
                                    msg,
                                    self.post))

        return msg

    def on(self):
        self.active = True

    def off(self):
        self.active = False


class TracebackWrapper(MessageWrapper):
    """
    Base class for printing and modifying stack traceback
    """
    trim_ipython_stack = True

    def __init__(self, title='Traceback', width=80, char='-'):
        super().__init__(self._format_stack, title, width, char)

    def _format_stack(self):
        stack = traceback.format_stack()
        # if we are in IPython, we do't actually want to print the entire
        # stack containing all the IPython code execution boilerplate noise,
        # so we filter all that here
        new_stack = stack
        # if is_interactive():  # and self.trim_ipython_stack:
        #     trigger = "exec(compiler(f.read(), fname, 'exec'), glob, loc)"
        #     for i, s in enumerate(stack):
        #         if trigger in s:
        #             new_stack = ['< %i lines omitted >\n' % i] + stack[i:]
        #             break

        #     # should now be at the position where the real traceback starts

        #     # when code execution is does via a magic, there is even more
        #     # IPython lines in the stack. Remove
        #     # trigger = 'exec(code_obj, self.user_global_ns, self.user_ns)'

        #     # when we have an embeded terminal
        #     triggers = 'terminal/embed.py', 'TracebackWrapper'
        #     done = False
        #     for i, s in enumerate(new_stack):
        #         for j, trigger in enumerate(triggers):
        #             if trigger in s:
        #                 new_stack = new_stack[:i]
        #                 new_stack.append(
        #                     '< %i lines omitted >\n' % (len(stack) - i))
        #                 done = True
        #                 break
        #         if done:
        #             break

        #     # i += 1
        #     # # noinspection PyRedundantParentheses
        #     # if (len(stack) - i):
        #     #     msg += '\n< %i lines omitted >\n' % (len(stack) - i)

        # last few lines in the stack are those that wrap the warning
        # message, so we filter those
        # for s in stack:

        # for s in stack[i:]:
        #     if '_showwarnmsg' in s:
        #         # last few lines in the stack are those that wrap the warning
        #         # message, so we filter those
        #         break
        #
        #     msg += s
        return ''.join(new_stack)


class TracePrints(MessageWrapper):
    # TODO: as context wrapper : see contextlib.redirect_stdout
    """
    Class that can be used to find print statements in unknown source code

    Examples
    --------
    >>> sys.stdout = TracePrints()
    >>> print("I am here")
    """

    def __init__(self, title=None, width=80, char='='):
        super().__init__(lambda s: s, title, width, char)
        self.format_stack = TracebackWrapper()
        self.stdout = sys.stdout

    def _wrap_message(self, msg):
        return super()._wrap_message(
            os.linesep.join((msg, self.format_stack())))

    def write(self, s):
        # print() statements usually involve two calls to stdout.write
        # first to write the content, second to write a newline if we are
        # writing newline, skip the banner
        if (not self.active) or (s == os.linesep):
            self.stdout.write(s)
        else:
            self.stdout.write(self(s))

    def flush(self):
        self.stdout.flush()


class TraceWarnings(MessageWrapper):
    """
    Class that help to track down warning statements in unknowns source code
    """

    # if warnings.formatwarning is self._formatwarning

    def __init__(self, title=None, width=80, char='='):
        """
        Activate full traceback for warnings

        Parameters
        ----------

        Examples
        --------
        >>> wtb = TraceWarnings()
        >>> warnings.warn('Dinosaurs!')
        # TODO: generate this output dynamically ???

        ------------------------------- TraceWarnings -------------------------------
        /usr/local/lib/python3.5/dist-packages/ipykernel_launcher.py:5: UserWarning: Dinosaurs!
          File "/usr/lib/python3.5/runpy.py", line 193, in _run_module_as_main
            "__main__", mod_spec)
        ... <some lines omitted for brevity>
          File "/usr/lib/python3.5/warnings.py", line 18, in showwarning
            file.write(formatwarning(message, category, filename, lineno, line))
        --------------------------------------------------------------------------------

        >>> wtb.off()
        >>> warnings.warn('Dinosaurs!')
        /usr/local/lib/python3.5/dist-packages/ipykernel_launcher.py:1: UserWarning: Dinosaurs!
          Entry point for launching an IPython kernel.
        """

        super().__init__(warnings.formatwarning, title, width, char)
        self.format_stack = TracebackWrapper()
        self.on()

    def _wrap_message(self, msg):
        return super()._wrap_message(
            os.linesep.join((msg, self.format_stack())))

    def on(self):
        self.active = True
        warnings.formatwarning = self

    def off(self):
        self.active = False
        warnings.formatwarning = original_formatwarning

