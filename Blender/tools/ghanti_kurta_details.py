"""Kurta details for the bell-hearing boy: button placket, buttons and mandarin collar."""

from math import cos, sin, tau

from mathutils import Vector

from ghanti_common import body_weight, dominant, interp, smooth, stitches, thick_grid
from ghanti_kurta import KURTA_ROWS, kurta_point


def placket(c, m):
    columns = (-.0155, -.005, .005, .0155)
    grid, normals = [], []
    for k in range(14):
        z = 1.41 - .26 * k / 13
        rx = interp(KURTA_ROWS, z)[0]
        line, direction = [], []
        for x in columns:
            point, normal = kurta_point(x / rx, z, .0008)
            line.append(point)
            direction.append(normal)
        grid.append(line)
        normals.append(direction)
    thick_grid(c, 'Kurta button placket', grid, normals, .0034, m['trim'], body_weight)
    for edge, label in ((-1, 'left'), (1, 'right')):
        points, normals = [], []
        for k in range(26):
            z = 1.405 - .25 * k / 25
            rx = interp(KURTA_ROWS, z)[0]
            point, normal = kurta_point(edge * .0185 / rx, z, .0044)
            points.append(point)
            normals.append(normal)
        stitches(c, f'Placket stitching {label}', points, normals, m['thread'], body_weight,
                 width=.0013, lift=.0004)
    for index, z in enumerate((1.35, 1.29, 1.23, 1.17)):
        base, _ = kurta_point(0, z, .0062)
        weight = dominant(body_weight(Vector((0, 0, z))))
        c.ovoid(f'Kurta button {index + 1}', tuple(base), (.0078, .0034, .0078), m['button'], weight)
        ring = [tuple(base + Vector((.0046 * cos(tau * s / 14), -.0016, .0046 * sin(tau * s / 14))))
                for s in range(14)]
        c.tube(f'Button thread ring {index + 1}', ring, .0008, m['thread'], weight, cyclic=True)
        for hole in (-1, 1):
            c.ovoid(f'Button hole {index + 1}.{hole}', tuple(base + Vector((.0022 * hole, -.0030, 0))),
                    (.0010, .0007, .0010), m['thread'], weight)


def collar(c, m):
    """Mandarin collar, open at the front, with a folded top edge and stitching."""
    cols, spread = 40, 2.62
    grid, normals = [], []
    for k in range(6):
        t = k / 5
        z = 1.404 + .042 * t
        rx, ry = .071 - .007 * t, .066 - .007 * t
        line, direction = [], []
        for j in range(cols):
            theta = -spread + 2 * spread * j / (cols - 1)
            gap = 1 - .55 * smooth(.9, .0, abs(theta))
            direction.append(Vector((sin(theta) / rx, -cos(theta) / ry, 0)).normalized())
            line.append(Vector((rx * sin(theta) * gap, -.008 - ry * cos(theta), z)))
        grid.append(line)
        normals.append(direction)
    weight = lambda p: {'chest': .45, 'neck': .55} if p.z > 1.42 else 'chest'
    thick_grid(c, 'Kurta mandarin collar', grid, normals, .0042, m['cloth'], weight)
    edge = [tuple(grid[-1][j] + normals[-1][j] * .0042) for j in range(cols)]
    c.tube('Collar folded edge', edge, .0028, m['trim'], 'neck')
    points = [grid[3][j] + normals[3][j] * .0050 for j in range(cols)]
    stitches(c, 'Collar stitching', points, normals[3], m['thread'], lambda p: 'neck',
             width=.0012, lift=.0003)
