import numpy as np


# TODO: look for library that can represent rotation group else make one
# https: // en.wikipedia.org / wiki / Rotation_group_SO(3)

def rotate(xy, theta):
    # TODO: check shapes
    return rotation_matrix_2d(theta) @ xy


def rotate_degrees(xy, theta):
    return rotate(xy, np.radians(theta))


def rotation_matrix_2d(theta):
    """Rotation matrix"""
    cos = np.cos(theta)
    sin = np.sin(theta)
    return np.array([[cos, -sin],
                     [sin, cos]])


# aliases
rotation_matrix = rotation_matrix_2d
rotate_2d = rotate
rotate_degrees_2d = rotate_degrees

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
    axis /= np.sqrt((axis * axis).sum())

    # 'Rodriguez parameters'
    a = float(np.cos(theta / 2))
    b, c, d = -axis * np.sin(theta / 2)

    # Rotation matrix
    aa = a * a
    bb = b * b
    cc = c * c
    dd = d * d
    bc = b * c
    ad = a * d
    bd = b * d
    ac = a * c
    cd = c * d
    return  np.array([
        [aa + bb - cc - dd, 2 * (bc - ad),     2 * (bd + ac)],
        [2 * (bc + ad),     aa + cc - bb - dd, 2 * (cd - a * b)],
        [2 * (bd - ac),     2 * (cd + a * b),  aa + dd - bb - cc]
    ])


def rotate_3d(data, axis, theta):  # TODO: rename rotate_3d
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


def rotate_degrees_3d(data, axis, theta):
    """Rotate `data` about `axis` by `theta` degrees"""
    return rotate_3d(data, axis, np.radians(theta))
