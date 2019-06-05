# TODO: maybe recipes.maths.transforms.rotations

import numpy as np


# TODO: look for library that can rep rotation group else make one
# https: // en.wikipedia.org / wiki / Rotation_group_SO(3)


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
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return x, y


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
    r = np.sqrt(x * x + y * y)
    θ = np.arctan2(y, x)
    return r, θ


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

    return (r * np.sin(theta) * np.cos(phi),
            r * np.sin(theta) * np.sin(phi),
            r * np.cos(theta))


def rotation_matrix_2d(theta):
    """Rotation matrix"""
    cos = np.cos(theta)
    sin = np.sin(theta)
    return np.array([[cos, -sin],
                     [sin, cos]])


def rotate_2d(xy, theta):
    return rotation_matrix_2d(theta) @ xy


def rotation_matrix_3d(axis, theta):
    """
    Use Euler–Rodrigues formula to generate the 3x3 rotation matrix for
    rotation of `theta` radians about Cartesian direction vector `axis`.

    Any 3d rotation can be represented this way: see Euler's rotation theorem.
    These rotations have a group structure and can thus be composed to yield
    another rotation.

    see: https://en.wikipedia.org/wiki/Euler%E2%80%93Rodrigues_formula
    """

    axis = np.asarray(axis)
    axis = axis / np.sqrt((axis * axis).sum())

    # 'Rodriguez parameters'
    a = float(np.cos(theta / 2))
    b, c, d = -axis * np.sin(theta / 2)

    # Rotation matrix
    R = np.array([[a * a + b * b - c * c - d * d, 2 * (b * c - a * d),
                   2 * (b * d + a * c)],
                  [2 * (b * c + a * d), a * a + c * c - b * b - d * d,
                   2 * (c * d - a * b)],
                  [2 * (b * d - a * c), 2 * (c * d + a * b),
                   a * a + d * d - b * b - c * c]])
    return R


def rotate(data, axis, theta):  # TODO: rename rotate_3d
    """Rotate `data` about `axis` by `theta` radians"""
    # Cast array in shape for matrix
    # data = data.reshape(data.shape)
    # multiplication (shape will be (r,c,3,1) where X,Y,Z have shape (r,c))
    # TODO: deduce dimensionality from axis
    R = rotation_matrix_3d(axis, theta)  # 3x3 rotation matrix

    # Coordinate transform
    XR, YR, ZR = np.dot(R, data).squeeze()
    # (higher dimensional equivalent of Matrix multiplication by R on each
    # point x,y,z in X,Y,Z).  squeeze flattens singular dimensions
    return XR, YR, ZR


def rotate_deg(data, axis, theta):
    """Rotate `data` about `axis` by `theta` degrees"""
    return rotate(data, axis, np.radians(theta))
