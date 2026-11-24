"""Earth-brown knee shorts for the bell-hearing boy: folds, rolled cuffs, seams, knee patch, waistband."""

import math
from math import cos, sin, tau

from mathutils import Vector

from ghanti_common import interp, smooth, stitches, thick_grid


SHORTS_ROWS = (  # z, centre x, half-width x, half-depth y
    (.575, .133, .086, .087), (.640, .131, .090, .092), (.710, .127, .096, .098),
    (.780, .121, .099, .103), (.850, .108, .098, .108), (.935, .090, .086, .108),
)


def shorts_point(sign, angle, z, lift=0.):
    cx, rx, ry = interp(SHORTS_ROWS, z)
    ripple = (.0022 + .0100 * smooth(.70, .575, z) + .004 * smooth(.80, .935, z)) * (
        .6 * cos(5 * angle + 18 * z) + .4 * cos(9 * angle - 11 * z))
    normal = Vector((cos(angle) / rx, sin(angle) / ry, 0)).normalized()
    point = Vector((sign * cx + rx * (1 + ripple) * cos(angle), ry * (1 + ripple) * sin(angle), z))
    return point + normal * lift, normal


def legs(c, m):
    for sign, side in ((1, 'L'), (-1, 'R')):
        thigh = f'thigh.{side}'
        weight = lambda p, t=thigh: {t: .64, 'hips': .36} if p.z > .84 else t
        zs = [.575 + (.935 - .575) * i / 14 for i in range(15)]
        rings = [[shorts_point(sign, tau * j / 40, z)[0] for j in range(40)] for z in zs]
        c.ring_mesh(f'Knee-length shorts {side}', rings, m['shorts'],
                    [weight(Vector((0, 0, z))) for z in zs], cap=False)

        cuff = [[shorts_point(sign, tau * j / 40, z, bulge)[0] for j in range(40)]
                for z, bulge in ((.572, .0008), (.578, .0095), (.606, .0105), (.628, .0070), (.634, .0010))]
        c.ring_mesh(f'Shorts rolled cuff {side}', cuff, m['trim'], [thigh] * 5, cap=False)
        points, normals = [], []
        for j in range(81):
            point, normal = shorts_point(sign, tau * (j % 80) / 80, .618, .0112)
            points.append(point)
            normals.append(normal)
        stitches(c, f'Shorts cuff stitching {side}', points, normals, m['thread'], weight,
                 width=.0014, lift=.0003)

        points, normals = [], []
        for k in range(30):
            point, normal = shorts_point(sign, 0 if sign == 1 else math.pi, .65 + .28 * k / 29, .0008)
            points.append(point)
            normals.append(normal)
        stitches(c, f'Shorts side seam stitching {side}', points, normals, m['thread'], weight, width=.0015)


def knee_patch(c, m):
    sign, thigh = -1, 'thigh.R'
    a0, a1, z0, z1 = -math.pi / 2 - .55, -math.pi / 2 + .55, .625, .725
    grid, normals = [], []
    for i in range(7):
        z = z0 + (z1 - z0) * i / 6
        line, direction = [], []
        for j in range(10):
            point, normal = shorts_point(sign, a0 + (a1 - a0) * j / 9, z, .0010)
            line.append(point)
            direction.append(normal)
        grid.append(line)
        normals.append(direction)
    thick_grid(c, 'Shorts knee patch', grid, normals, .0026, m['patch'], lambda p: thigh)
    corners = ((a0 + .06, z0 + .014), (a1 - .06, z0 + .014), (a1 - .06, z1 - .014),
               (a0 + .06, z1 - .014), (a0 + .06, z0 + .014))
    points, normals = [], []
    for (aa, za), (ab, zb) in zip(corners, corners[1:]):
        for k in range(10):
            u = k / 10
            point, normal = shorts_point(sign, aa + (ab - aa) * u, za + (zb - za) * u, .0040)
            points.append(point)
            normals.append(normal)
    points.append(points[0])
    normals.append(normals[0])
    stitches(c, 'Knee patch stitching', points, normals, m['thread'], lambda p: thigh, width=.0015)


def waistband(c, m):
    """Gathered waistband and drawstring, visible when the kurta lifts."""
    rings = []
    for z, rx, ry, gather in ((.925, .176, .121, .002), (.960, .178, .122, .004), (.995, .174, .119, .004)):
        rings.append([(rx * (1 + gather * cos(22 * tau * j / 110)) * cos(tau * j / 110),
                       ry * (1 + gather * cos(22 * tau * j / 110)) * sin(tau * j / 110), z)
                      for j in range(110)])
    c.ring_mesh('Shorts gathered waistband', rings, m['shorts'], ['hips'] * 3, cap=False)
    cord = [(.1795 * cos(tau * j / 64), .1235 * sin(tau * j / 64), .958) for j in range(64)]
    c.tube('Shorts drawstring', cord, .0042, m['trim'], 'hips', cyclic=True)
