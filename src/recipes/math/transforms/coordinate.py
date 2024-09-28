"""
Common coordinate transformations.
"""

import numpy as np


# ---------------------------------------------------------------------------- #

def pol2cart(r, theta):
    """
    Polar to Cartesian transformation.

    Parameters
    ----------
    r
    theta

    Returns
    -------

    """
    return (r * np.cos(theta),  # x
            r * np.sin(theta))  # y


def cart2pol(x, y):
    """
    Cartesian 2d to polar transformation.

    Parameters
    ----------
    x
    y

    Returns
    -------

    """
    return (np.sqrt(x*x + y*y),     # r
            np.arctan2(y, x))       # θ


def sph2cart(r, theta, phi):
    """
    Transform spherical polar (r,θ,φ) to Cartesian (x,y,z) coordinates.
    Parameter definitions are as per physics (ISO 80000-2:2019) convention with
    φ the azimuth and θ the colatitude.

    Parameters
    ----------
    r
    theta
    phi

    Returns
    -------

    """
    r_sinθ = r * np.sin(theta)
    return (r_sinθ * np.cos(phi),
            r_sinθ * np.sin(phi),
            r * np.cos(theta))


def cart2sph(x, y, z):
    """
    Transform Cartesian (x,y,z) to spherical polar (r,θ,φ).

    Parameters
    ----------
    r
    theta
    phi
    key

    Returns
    -------
    (r,θ,φ) : float, np.ndarray
        Definitions are as per physics (ISO 80000-2:2019) convention with θ the
        azimuth and φ the colatitude.
    """
    return (r := np.sqrt(x*x + y*y + z*z),
            np.arccos(z / r),
            np.arctan2(y, x))
