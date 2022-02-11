"""
A few basic coordinate transformers
"""


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

def rotate(xy, theta):
    # Xnew = (rot @ np.transpose(X)).T
    # xy2 = np.matmul(rot, np.transpose(xy)).T
    # einsum is about 2x faster than using @ and transposing twice, and about
    # 1.5x faster than np.matmul with 2 transposes
    return np.einsum('ij,...hj', rotation_matrix(theta), np.atleast_2d(xy))


def rigid(xy, p):
    """
    A rigid transformation of the 2 dimensional cartesian coordinates `X`. A
    rigid transformation represents a rotatation and/or translation of a set of
    coordinate points, and is also known as a roto-translation, Euclidean
    transformation or Euclidean isometry depending on the context.

    See: https://en.wikipedia.org/wiki/Rigid_transformation

    Parameters
    ----------
    xy: np.ndarray
         shape (n_samples, 2)
    p: np.ndarray
         δx, δy, θ

    Returns
    -------
    np.ndarray

    """
    return rotate(xy, p[-1]) + p[:2]

def affine(xy, p, scale=1):
    return rigid(xy * scale, p)