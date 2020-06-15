from .rotation import *


def pol2cart(r, theta):
    """
    Polar to Cartesian transformation

    Parameters
    ----------
    r
    theta

    Returns
    -------

    """
    return (r * np.cos(theta),
            r * np.sin(theta))


def cart2pol(x, y):
    """
    Cartesian 2d to polar transformation

    Parameters
    ----------
    x
    y

    Returns
    -------

    """
    return (np.sqrt(x * x + y * y),  # r
            np.arctan2(y, x))        # θ


def sph2cart(r, theta, phi, key=None):
    """
    Spherical polar to cartesian transformation

    Parameters
    ----------
    r
    theta
    phi
    key

    Returns
    -------

    """
    if key == 'grid':
        theta = np.atleast_2d(theta).T

    r_sinθ = r * np.sin(theta)
    return (r_sinθ * np.cos(phi),
            r_sinθ * np.sin(phi),
            r * np.cos(theta))