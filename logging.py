import logging
import functools

from decor.base import DecoratorBase

# ****************************************************************************************************
class LoggingMixin():
    basename = ''
    show_module = True

    @property       #NOTE: making this a property avoids pickling error for the logger
    def logger(self):
        cls = type(self)
        parts = filter(None, (self.basename,
                              cls.__module__ if self.show_module else '',
                              cls.__name__)
                       )
        component = '.'.join(parts)
        return logging.getLogger(component)


# ====================================================================================================
class catch_and_log(DecoratorBase, LoggingMixin):
    '''Decorator that catches and logs errors instead of actively raising'''
    # basename = 'log'        #base name of the log - to be set at module level

    def __init__(self, func):
        super().__init__(func)

        #NOTE: partial functions don't have the __name__, __module__ attributes!
        #retriev the deepest func attribute -- the original func
        while isinstance(func, functools.partial):
            func = func.func
        self.__module__ = func.__module__
        self.__name__ = 'partial(%s)' %func.__name__

    def __call__(self, *args, **kws):
        try:
            result = self.func(*args, **kws)
            return result
        except Exception as err:
            self.logger.exception('%s' % str(args))  # logs full trace by default