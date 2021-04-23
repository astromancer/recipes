
# pylint: disable-all

if isinstance(other, TimeSeries):
    # Can only really do time series if they are simultaneous
    if self.n != other.n:
        raise ValueError('Arithmetic on %s objects with different '
                         'sizes not permitted' % self.__class__)


if n > N_MAX_TS_SAFETY:
    raise TooManyToPlot(
        'Received %i time series to plot. This is probably not what you wanted. Refusing since safety limit '
        'is currently set to %i to avoid accidental compute intensive '
        'commands from overwhelming system resources.'
        % (n, N_MAX_TS_SAFETY))


if (colours is not None) and (len(colours) < n):
    logger.warning('Colour sequence has too few colours (%i < %i). Colours '
                   'will repeat' % (len(colours), n))

n = len(data)
if 4 < n < 1:
    raise ValueError('Invalid number of arguments: %i' % n)


if len(times) != len(signals):
    raise ValueError('Number of time and signal vectors do not correspond. Please provide explicit time stamps for all signal vectors when plotting ragged time series.'
                        )