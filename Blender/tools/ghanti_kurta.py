"""Kurta body surface of the bell-hearing boy: shape functions, body, hem and side seams."""

import math
from math import cos, sin, tau

from mathutils import Vector

from ghanti_common import body_weight, interp, smooth, stitches


KURTA_ROWS = (  # z, half-width x, half-depth y, centre y
    (.930, .188, .130, 0.), (.990, .182, .126, 0.), (1.050, .172, .119, 0.),
    (1.110, .164, .113, 0.), (1.170, .168, .115, 0.), (1.240, .186, .119, 0.),
    (1.300, .198, .117, 0.), (1.345, .200, .108, -.001), (1.378, .188, .096, -.003),
    (1.400, .152, .081, -.005), (1.413, .102, .067, -.007), (1.420, .068, .059, -.008),
)
SLEEVE_X = (.13, .16, .19, .22, .25, .28, .305, .325)
SLEEVE_R = (.050, .058, .064, .069, .073, .076, .078, .080)  # rounded shoulder cap, loose at the cuff


def kurta_ripple(theta, z):
    amplitude = .0016 + .0045 * smooth(1.30, 1.12, z) + .020 * smooth(1.08, .93, z)
    folds = (.55 * cos(6 * theta + .8 + 3 * z) + .30 * cos(11 * theta + 2. - 5 * z)
             + .15 * cos(17 * theta + 7 * z))
    return amplitude * folds * (.35 + .65 * sin(theta / 2) ** 2)


def kurta_point(theta, z, lift=0.):
    """Surface point (theta 0 = centre front, increasing towards the wearer's left) and outward normal."""
    rx, ry, cy = interp(KURTA_ROWS, z)
    factor = 1 + kurta_ripple(theta, z)
    normal = Vector((sin(theta) / rx, -cos(theta) / ry, 0)).normalized()
    point = Vector((rx * factor * sin(theta), cy - ry * factor * cos(theta), z))
    return point + normal * lift, normal


def sleeve_point(sign, x, a, lift=0.):
    radius = interp(tuple(zip(SLEEVE_X, SLEEVE_R)), x)[0]
    t = max(0., (x - .17) / .17)
    radius *= 1 + (.004 + .030 * t) * cos(5 * a + 20 * x)
    centre_z = 1.364 + .008 * min(1., t * 2) - .012 * t * t  # follows the sloping shoulder
    normal = Vector((0, sign * cos(a), sin(a)))
    point = Vector((sign * x, sign * radius * cos(a), centre_z + radius * sin(a)))
    return point + normal * lift, normal


def kurta_patch(theta0, theta1, z0, z1, cols, rows, lift):
    grid, normals = [], []
    for i in range(rows):
        z = z0 + (z1 - z0) * i / (rows - 1)
        line, direction = [], []
        for j in range(cols):
            point, normal = kurta_point(theta0 + (theta1 - theta0) * j / (cols - 1), z, lift)
            line.append(point)
            direction.append(normal)
        grid.append(line)
        normals.append(direction)
    return grid, normals


def border_path(theta0, theta1, z0, z1, lift, spacing=.011):
    """Closed rectangle in (theta, z) space, sampled at stitch spacing."""
    corners = ((theta0, z0), (theta1, z0), (theta1, z1), (theta0, z1), (theta0, z0))
    points, normals = [], []
    for (ta, za), (tb, zb) in zip(corners, corners[1:]):
        a, _ = kurta_point(ta, za)
        b, _ = kurta_point(tb, zb)
        count = max(2, int((b - a).length / spacing))
        for k in range(count):
            u = k / count
            point, normal = kurta_point(ta + (tb - ta) * u, za + (zb - za) * u, lift)
            points.append(point)
            normals.append(normal)
    points.append(points[0])
    normals.append(normals[0])
    return points, normals


def line_path(theta0, z0, theta1, z1, count, lift):
    points, normals = [], []
    for k in range(count):
        u = k / (count - 1)
        point, normal = kurta_point(theta0 + (theta1 - theta0) * u, z0 + (z1 - z0) * u, lift)
        points.append(point)
        normals.append(normal)
    return points, normals


def body(c, m):
    """Rippled torso tube, rolled hem with stitching, side seams and bar-tacks."""
    segments, rows = 96, 69
    zs = [.93 + (1.42 - .93) * i / (rows - 1) for i in range(rows)]
    rings = [[kurta_point(tau * j / segments, z)[0] for j in range(segments)] for z in zs]
    c.ring_mesh('Kurta body', rings, m['cloth'], [body_weight(Vector((0, 0, z))) for z in zs], cap=False)
    c.tube('Kurta rolled hem', rings[0], .0048, m['trim'], 'hips', cyclic=True)

    points, normals = [], []
    for j in range(segments * 2 + 1):
        point, normal = kurta_point(tau * (j % (segments * 2)) / (segments * 2), .962, .0003)
        points.append(point)
        normals.append(normal)
    stitches(c, 'Kurta hem stitching', points, normals, m['thread'], body_weight)

    for sign, label in ((1, 'L'), (-1, 'R')):
        theta = sign * math.pi / 2
        points, normals = line_path(theta, .97, theta, 1.30, 36, .0008)
        stitches(c, f'Kurta side seam stitching {label}', points, normals, m['thread'], body_weight,
                 width=.0015)
        base, normal = kurta_point(theta, 1.015, .0012)
        c.ovoid(f'Slit bar-tack {label}', tuple(base), (.0045, .0045, .0105), m['thread'], 'hips',
                (0, 0, math.atan2(normal.y, normal.x)))
