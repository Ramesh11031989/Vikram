"""Kurta pocket, mended patch and sleeves for the bell-hearing boy."""

import math
from math import tau

from mathutils import Vector

from ghanti_common import body_weight, stitches, thick_grid
from ghanti_kurta import SLEEVE_X, border_path, kurta_patch, line_path, sleeve_point


def pockets_and_patch(c, m):
    t0, t1, z0, z1 = -.98, -.50, .995, 1.085
    grid, normals = kurta_patch(t0, t1, z0, z1, 12, 8, .0010)
    thick_grid(c, 'Kurta patch pocket', grid, normals, .0030, m['cloth'], body_weight)
    top_edge = [tuple(grid[-1][j] + normals[-1][j] * .0030) for j in range(12)]
    c.tube('Pocket top hem', top_edge, .0030, m['trim'], 'spine')
    points, normals = border_path(t0 + .03, t1 - .03, z0 + .014, z1 - .018, .0042)
    stitches(c, 'Pocket stitching', points, normals, m['thread'], body_weight)

    # Mended chest patch: a different ochre homespun square, cross-stitched.
    t0, t1, z0, z1 = .46, .84, 1.135, 1.235
    grid, normals = kurta_patch(t0, t1, z0, z1, 10, 8, .0011)
    thick_grid(c, 'Kurta mended patch', grid, normals, .0026, m['patch'], body_weight)
    points, normals = border_path(t0 + .025, t1 - .025, z0 + .012, z1 - .012, .0040, spacing=.009)
    stitches(c, 'Mended patch stitching', points, normals, m['thread'], body_weight, width=.0015)
    for label, (ta, za, tb, zb) in (('A', (t0 + .03, z0 + .012, t1 - .03, z1 - .012)),
                                    ('B', (t0 + .03, z1 - .012, t1 - .03, z0 + .012))):
        points, normals = line_path(ta, za, tb, zb, 16, .0040)
        stitches(c, f'Mended patch cross stitch {label}', points, normals, m['thread'],
                 body_weight, width=.0012)


def sleeves(c, m):
    """Loose short sleeves with a turned cuff, cuff stitching and a shoulder seam."""
    for sign, side in ((1, 'L'), (-1, 'R')):
        upper = f'upper_arm.{side}'
        stations = [SLEEVE_X[0] + (SLEEVE_X[-1] - SLEEVE_X[0]) * i / 17 for i in range(18)]
        rings = [[sleeve_point(sign, x, tau * j / 48)[0] for j in range(48)] for x in stations]

        def arm_weight(x, u=upper):
            t = min(1., max(0., (x - .14) / .12))   # shoulder joins the chest, then follows the arm
            return 'chest' if t <= 0 else u if t >= 1 else {'chest': 1 - t, u: t}

        c.ring_mesh(f'Kurta sleeve {side}', rings, m['cloth'], [arm_weight(x) for x in stations])
        cuff = []
        for x, bulge in ((.322, 0.), (.328, .0075), (.341, .0075), (.347, 0.)):
            ring = []
            for j in range(36):
                point, normal = sleeve_point(sign, .325, tau * j / 36)
                ring.append(Vector((sign * x, point.y, point.z)) + normal * (bulge + .001))
            cuff.append(ring)
        c.ring_mesh(f'Sleeve turned cuff {side}', cuff, m['trim'], [upper] * 4, cap=False)
        points, normals = [], []
        for j in range(73):
            point, normal = sleeve_point(sign, .3345, tau * (j % 72) / 72, .0090)
            points.append(point)
            normals.append(normal)
        stitches(c, f'Sleeve cuff stitching {side}', points, normals, m['thread'],
                 lambda p, u=upper: u, width=.0014, lift=.0003)
        points, normals = [], []
        for k in range(22):
            point, normal = sleeve_point(sign, .14 + .17 * k / 21, math.pi / 2, .0008)
            points.append(point)
            normals.append(normal)
        stitches(c, f'Shoulder seam stitching {side}', points, normals, m['thread'],
                 lambda p, u=upper: {'chest': .6, u: .4} if abs(p.x) < .2 else u, width=.0015)
