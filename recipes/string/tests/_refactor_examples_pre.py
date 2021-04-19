

class _Test1
    def _arithmetic(self, other, op):
        #
        if isinstance(other, TimeSeries):
            # Can only really do time series if they are simultaneous
            if self.n != other.n:
                raise ValueError('Arithmetic on %s objects with different '
                                 'sizes not permitted' % self.__class__)