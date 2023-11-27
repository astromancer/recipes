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

        self.axis = (v := np.asarray(axis, float)) / np.sqrt((v * v).sum())
        self.theta = θ = float(theta)

        # 'Rodriguez parameters'
        a = np.cos(θ / 2)
        b, c, d = -self.axis * np.sin(θ / 2)

        # Rotation matrix
        aa, ac, ad = np.multiply(a, (a, c, d))
        bb, bc, bd = np.multiply(b, (b, c, d))
        cc, cd = np.multiply(c, (c, d))
        dd = d * d

        self.matrix = np.array([
            [aa + bb - cc - dd,     2 * (bc - ad),          2 * (bd + ac)],
            [2 * (bc + ad),         aa + cc - bb - dd,      2 * (cd - a * b)],
            [2 * (bd - ac),         2 * (cd + a * b),       aa + dd - bb - cc]
        ])


class SphericalRotationMatrix:
    def __init__(self, alt=0, az=0):
        sinθ, cosθ = np.sin(alt), np.cos(alt)
        sinφ, cosφ = np.sin(az),  np.cos(az)

        self.matrix = np.array([
            [sinθ * cosφ,   sinθ * sinφ,    cosθ],
            [cosθ * cosφ,   cosθ * sinφ,    -sinθ],
            [-sinφ,         cosφ,           0]
        ])


# def rotation_matrix_3d(axis, theta):
#     return EulerRodrigues(axis, theta).matrix


def rotate_about_axis(data, axis, theta):
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
    return np.dot(EulerRodrigues(axis, theta).matrix, data)  # .squeeze()


rotate_3d = rotate_about_axis


def rotate_degrees_about(data, axis, theta):
    """Rotate `data` about `axis` by `theta` degrees"""
    return rotate_about_axis(data, axis, np.radians(theta))
