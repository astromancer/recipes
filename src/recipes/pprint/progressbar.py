# std
import os
import sys
import math

# relative
from ..misc import get_terminal_size
from ..strng import overlay, resolve_percentage


def move_cursor(val):
    """move cursor up or down"""
    AB = 'AB'[val > 0]  # move up (A) or down (B)
    mover = '\033[{}{}'.format(abs(val), AB)
    sys.stdout.write(mover)


class ProgressBarBase:
    def __init__(self, precision=2, width=None, symbol='=', align='^',
                 sides='|', every=None):
        """ """
        self.sigfig = precision
        self.symbol = str(symbol)
        self.sides = str(sides)
        self.align = align  # centering for percentage, info
        if width is None:
            width = get_terminal_size()[0]
        self.width = int(width)
        # self.bar = ''
        # if pfmt is None:
        #     pfmt =
        self.pfmt = '{0:.%i%%}' % self.sigfig
        self.count = 0
        self.end = 0  # will be set upon call to create
        self.every = every  # how frequently progressbar will emit during loop
        self.stream = None

    def create(self, end, stream=sys.stdout):
        """create the bar and move cursor to it's center"""
        # NOTE: sys.stdout makes this class un-picklable
        assert end > 0
        self.end = int(end)
        every = resolve_percentage(self.every, self.end)
        if every is None:
            # only update once progress has advanced enough to change text
            every = math.ceil(10 ** (self.sigfig + 2) / self.end)
        self.every = max(every, 1)
        self.stream = stream

    def inc(self):
        self.count += 1
        return int(self.count)

    def update(self, i=None):  # stream ??
        """

        Parameters
        ----------
        i: int
            Optional current state. Pass this in if you want the progress bar to update
            to that specific state. If missing, we increment to the next state

        Returns
        -------

        """
        if i is None:
            i = self.inc()
            # don't update when unnecessary
            if not self.needs_update(i):
                return

        # always update when index given
        if i >= self.end:  # unless state beyond end
            return

        bar = self.get_bar(i)
        self.stream.write('\r' + bar)

        if i == self.end - 1:
            self.close()
            return

        self.stream.flush()

    def get_bar(self, i):
        bar, percentage = self.format(i + 1)
        return overlay(percentage, bar, self.align)

    def format(self, i):
        """Make progress/percentage indicator strings"""

        frac = i / self.end
        # percentage completeness displayed to sigfig decimals
        percentage = self.pfmt.format(frac)

        # integer fraction of completeness of for loop.
        w = self.width - len(self.sides)
        ifb = int(round(frac * w))

        # filled up to 'width' in whitespaces
        bar = (self.symbol * ifb).ljust(w)
        bar = self.sides + bar + self.sides

        return bar, percentage

    def needs_update(self, i):
        """
        Only need to update the output stream if something has changed in the repr.
        ie. if the state i is significantly different from the current state.
        """
        return (not bool(i % self.every)) or (i == self.end - 1)

    def close(self):
        self.stream.write(os.linesep * 4)  # move the cursor down 4 lines
        # self.stream.flush()


class ProgressLogger(ProgressBarBase):
    def __init__(self, precision=2, width=None, symbol='=', align='^',
                 sides='|', every='2.5%', logname='progress'):
        ProgressBarBase.__init__(self, precision, width, symbol, align, sides,
                                 every)
        self.name = logname

    def update(self, i=None):
        if i is None:
            i = self.inc()

        # don't update when unnecessary
        if not self.needs_update(i):
            return

        # always update when state given
        if i >= self.end:  # unless state beyond end
            return

        bar = self.get_bar(i)
        logger.info('Progress: \n{:s}' % bar)

# class SyncedProgressLogger(ProgressLogger):
#     """can be used from multiple processes"""
#      def __init__(self, counter, precision=2, width=None, symbol='=', align='^', sides='|',
#                  logname='progress'):
#          ProgressLogger.__init__(self, precision, width, symbol, align, sides, logname)
#          self.counter = counter


# class ProgressLogger(ProgressBar, LoggingMixin):
#     # def __init__(self, **kws):
#     #     ProgressBar.__init__(self, **kws)
#     #     if not log_progress:
#     #         self.progress = null_func

#     def create(self, end):
#         self.end = end
#         self.every = np.ceil((10 ** -(self.sigfig + 2)) * self.end)
#         # only have to update text every so often

#     def progress(self, state, info=None):
#         if self.needs_update(state):
#             bar = self.get_bar(state)
#             logger.info('Progress: %s' % bar)


# class ProgressPrinter(ProgressBar):
#     def __init__(self, **kws):
#         ProgressBar.__init__(self, **kws)
#         if not print_progress:
#             self.progress = self.create = null_func

# def progressFactory(log=True, print_=True):
#     if not log:
#         global ProgressLogger  # not sure why this is needed

#         class ProgressLogger(ProgressLogger):
#             progress = null_func

#     if not print_:
#         class ProgressPrinter(ProgressBar):
#             progress = create = null_func

#     return ProgressLogger, ProgressBar
