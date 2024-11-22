"""
Spatial affine transforms.
"""


import numpy as np


# TODO: look for library that can represent rotation group else make one
# https: // en.wikipedia.org / wiki / Rotation_group_SO(3)

# ---------------------------------------------------------------------------- #

def rotate(points, angle, axis=None):

    points = np.atleast_2d(points)
    nspace = points.shape[-1]
    if nspace not in {2, 3}:
        raise ValueError(
            f'Invalid dimensions for coordinate array `points`: {points.shape}.'
            ' Last axis should have size 2 or 3.'
        )

    if nspace == 2:
        assert axis is None
        return rotate_2d(points, angle)

    if axis is None:
        # rotate about z axis by default. This means 2d vectors on the xy plane
        # rotate the same way as they would in 3d which is nice.
        axis = [*([0] * (nspace - 1)), 1]

    axis = np.array(axis).squeeze()
    assert len(axis) == 3
    return rotate_about_axis(points, axis, angle)


def rotate_2d(xy, theta):
    """
    Rotate cartesian coordinates `xy` be `theta` radians.

    Parameters
    ----------
    xy: np.ndarray
        shape (n_samples, 2).
    theta : float
        angle of rotation in radians.

    Returns
    -------
    np.ndarray
        transformed coordinate points.
    """

    # NOTE:
    # einsum is about 2x faster than using @ and transposing twice, eg:
    # >>> xyt = (rot @ np.transpose(xy)).T
    # and about 1.5x faster than np.matmul with 2 transposes eg:
    # >>> xyt = np.matmul(rot, np.transpose(xy)).T

    xy = np.atleast_2d(xy)

    if (xy.ndim > 2) or (xy.shape[-1] != 2):
        raise ValueError('Invalid dimensions for coordinate array `xy`.')

    return np.einsum('ij,...hj', rotation_matrix_2d(theta), xy)


def rotate_degrees(xy, theta):
    return rotate_2d(xy, np.radians(theta))


def rotation_matrix_2d(theta):
    """Rotation matrix"""
    cos = np.cos(theta)
    sin = np.sin(theta)
    return np.array([[cos, -sin],
                     [sin, cos]])


# aliases
rotation_matrix = rotation_matrix_2d
rotate_degrees_2d = rotate_degrees


# ---------------------------------------------------------------------------- #
# def rotation_matrix_3d(theta, axis=(0, 0, 1)):
#     return EulerRodrigues(axis, theta).matrix


def rotate_about_axis(points, axis, theta):
    """
    Rotate `data` about `axis` by `theta` radians.
    """
    # Cast array in shape for matrix
    # data = data.reshape(data.shape)
    # multiplication (shape will be (r,c,3,1) where X,Y,Z have shape (r,c))
    # TODO: deduce dimensionality from axis
    # R = rotation_matrix_3d(axis, theta)  # 3x3 rotation matrix

    # Coordinate transform
    # XR, YR, ZR = np.dot(R, data).squeeze()
    # (higher dimensional equivalent of Matrix multiplication by R on each
    # point x,y,z in X,Y,Z).  squeeze flattens singular dimensions
    # return XR, YR, ZR
    return np.dot(EulerRodriguesMatrix(axis, theta).matrix, points)  # .squeeze()


# alias
rotate_3d = rotate_about_axis


def rotate_degrees_about(points, axis, theta):
    """Rotate `points` about `axis` by `theta` degrees."""
    return rotate_about_axis(points, axis, np.radians(theta))


class SphericalRotationMatrix:

    def __init__(self, alt=0, az=0):
        sinθ, cosθ = np.sin(alt), np.cos(alt)
        sinφ, cosφ = np.sin(az),  np.cos(az)

        self.matrix = np.array([
            [sinθ * cosφ,   sinθ * sinφ,    cosθ],
            [cosθ * cosφ,   cosθ * sinφ,    -sinθ],
            [-sinφ,         cosφ,           0]
        ])


class EulerRodriguesMatrix:

    def __init__(self, axis, theta):
        """
        Use Euler–Rodrigues formula to generate the 3x3 rotation matrix for
        rotation of `theta` radians about Cartesian direction vector `axis`.

        Any 3d rotation can be represented this way: see Euler's rotation
        theorem. These rotations have a group structure and can thus be composed
        to yield another rotation.

        see: https://en.wikipedia.org/wiki/Euler%E2%80%93Rodrigues_formula
        """

        # normalize
        self.axis = (v := np.asarray(axis, float)) / np.sqrt((v * v).sum())
        self.theta = float(theta)

    @property
    def matrix(self):
        θ = self.theta
        # Rodriguez parameters
        a, (b, c, d) = (np.cos(θ / 2), -np.sin(θ / 2) * self.axis)

        # Rotation matrix
        aa, ac, ad = np.multiply(a, (a, c, d))
        bb, bc, bd = np.multiply(b, (b, c, d))
        cc, cd = np.multiply(c, (c, d))
        dd = d * d

        return np.array([
            [aa + bb - cc - dd,     2 * (bc - ad),          2 * (bd + ac)],
            [2 * (bc + ad),         aa + cc - bb - dd,      2 * (cd - a * b)],
            [2 * (bd - ac),         2 * (cd + a * b),       aa + dd - bb - cc]
        ])


# ---------------------------------------------------------------------------- #
# Affine transforms
# TODO: 3D support

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
        Data array shape (n, 2)
    p: np.ndarray
        Parameter array (δx, δy, θ)

    Returns
    -------
    np.ndarray
        Transformed coordinate points shape (n_samples, 2).

    """

    if len(p) != 3:
        raise ValueError('Invalid parameter array for rigid transform `xy`.')

    return rotate_2d(xy, p[-1]) + p[:2]


# alias
euclidean = rigid


def affine(xy, p, scale=1):
    """
    An affine transform.

    Parameters
    ----------
    xy: np.ndarray
        Coordinates, shape (n_samples, 2).
    p: np.ndarray
         δx, δy, θ
    scale : int, optional
        Scale coordinates before translating and rotating, by default 1.

    Returns
    -------
    np.ndarray
        Transformed coordinate points shape (n_samples, 2).
    """
    return rigid(xy * scale, p)
