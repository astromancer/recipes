import math
import os
import sys

from recipes.misc import get_terminal_size
from recipes.string import overlay, resolve_percentage


# import time
# import functools
# from . import codes


def move_cursor(val):
    """move cursor up or down"""
    AB = 'AB'[val > 0]  # move up (A) or down (B)
    mover = '\033[{}{}'.format(abs(val), AB)
    sys.stdout.write(mover)


class ProgressBarBase(object):
    def __init__(self, precision=2, width=None, symbol='=', align='^', sides='|',
                 every=None):  # , pfmt=None):
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
        self.every = every # explicitly say how often you want the progressbar to emit
        self.stream = None

    def create(self, end, stream=sys.stdout):
        """create the bar and move cursor to it's center"""
        # NOTE: sys.stdout makes this class un-picklable
        assert end > 0
        self.end = int(end)
        every = resolve_percentage(self.every, self.end)
        if every is None:
            # only have to update when progress has advanced enough to change text
            every = math.ceil(10 ** (self.sigfig + 2) / self.end)
        self.every = every
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

        # always update when state given
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
        """Make progress/percentage indicator strings."""

        frac = i / self.end
        # percentage completeness displayed to sigfig decimals
        percentage = self.pfmt.format(frac)

        w = self.width - len(self.sides)
        ifb = int(round(frac * w))  # integer fraction of completeness of for loop.

        bar = (self.symbol * ifb).ljust(w)  # filled up to 'width' in whitespaces
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
