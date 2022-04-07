import numbers, math


def signum(n):
    if n == 0:
        return 0

    if n < 0:
        return -1

    return 1


def order_of_magnitude(n, base=10):
    """
    Order of magnitude for a scalar.

    Parameters
    ----------
    n: numbers.Real
    base: int

    Returns
    -------

    """
    if not isinstance(n, numbers.Real):
        raise ValueError('Only scalars are accepted by this function.')

    if n == 0:
        return -math.inf

    logn = math.log(abs(n), base)
    # NOTE that the rounding error on log calculation is such that `logn`
    # may be slightly less than the correct theoretical answer. Eg:
    # log(1e12, 10) gives 11.999999999999998.  We need to round to get the
    # correct order of magnitude.
    return math.floor(round(logn, 9))  # returns an int