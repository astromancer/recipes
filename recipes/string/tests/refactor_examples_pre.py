

class _Test1
    def _arithmetic(self, other, op):
        #
        if isinstance(other, TimeSeries):
            # Can only really do time series if they are simultaneous
            if self.n != other.n:
                raise ValueError(f'Arithmetic on {self.__class__} objects with'
                                 f' different sizes not permitted')