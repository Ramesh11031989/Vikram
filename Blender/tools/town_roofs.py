"""Detailed roofs for the town set: layered thatch hips and corrugated clay-tile gables."""

import math
import random

from mathutils import Vector

import ghat_kit as k
from town_hard import Hard


def _noise(s, seed):
    return (math.sin(s * 2.3 + seed) * .5 + math.sin(s * 5.1 + seed * 1.7) * .3 + math.sin(s * 11.7 + seed * .4) * .2)


def thatch_ring(a, b, r, t, z, rise, out, per_side, seed, ragged=0.):
    """One closed ring of the hip roof at height fraction t (0 eave .. 1 ridge), pushed `out` outward."""
    x, y = a + (r - a) * t + out, b * (1 - t) + out
    corners = ((x, -y), (x, y), (-x, y), (-x, -y))
    points = []
    for i in range(4):
        c0, c1 = corners[i], corners[(i + 1) % 4]
        for j in range(per_side):
            u = j / per_side
            px, py = c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u
            sag = -ragged * (.5 + .5 * _noise(len(points) * .9, seed))
            points.append(Vector((px, py, z + rise * t + sag)))
    return points


def thatch_hip(b, w, d, z, rise, overhang, ridge_len, materials, seed=1, tiers=15):
    """Tiered bundles of straw: each tier steps out like laid thatch, with a ragged eave edge."""
    rng = random.Random(seed)
    a, bb, r = w / 2 + overhang, d / 2 + overhang, ridge_len / 2
    per_side = 12
    rings = []
    for i in range(tiers):
        step = .045 + rng.uniform(0, .02)
        low = thatch_ring(a, bb, r, i / tiers * .96, z, rise, step, per_side, seed + i, .10 if i == 0 else .02)
        high = thatch_ring(a, bb, r, (i + .88) / tiers * .96, z, rise, 0., per_side, seed + i + 50)
        rings += [low, high]
    n = len(rings[0])
    verts = [p for ring in rings for p in ring]
    faces = []
    for i in range(len(rings) - 1):
        for j in range(n):
            faces.append((i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j))
    faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    faces.append(tuple(reversed(range(n))))
    b.add(verts, faces, materials[0])
    top_z = z + rise * .96
    roll = [(-r - .15 + (2 * r + .3) * i / 8, 0, top_z + .08) for i in range(9)]
    b.tube(roll, lambda t: .21 * (1 - .12 * (2 * t - 1) ** 2), materials[0], sides=12)
    for i in range(7):
        x = -r + 2 * r * i / 6
        b.tube([(x, -.30, top_z - .03), (x, 0, top_z + .30), (x, .30, top_z - .03)], .017, materials[1], sides=5)
    b.tube([(-r - .2, 0, top_z + .13), (r + .2, 0, top_z + .13)], .028, materials[1], sides=6)


def tile_slope(b, w, d, z, rise, overhang, sign, tile, rng, courses=12):
    """One corrugated clay-tile slope (sign -1 faces -y, +1 faces +y), one tile every 0.16 m."""
    a, bb = w / 2 + overhang, d / 2 + overhang
    count = max(8, int(2 * a / .16))
    rows = []
    for c in range(courses):
        rows.append((c / courses, 0.))
        rows.append(((c + .93) / courses, .032))
    rows.append((1., .02))
    n = count + 1
    verts = []
    for v, lift in rows:
        for i in range(n):
            u = i / count
            x = -a + 2 * a * u
            pitch = rise / bb
            y = sign * bb * (1 - v)
            zz = z + rise * v
            wave = .013 * math.cos(u * count * math.tau) + rng.uniform(-.002, .002)
            nrm = Vector((0, sign * pitch, 1)).normalized()
            verts.append(Vector((x, y, zz)) + nrm * (lift + wave))
    faces = []
    for j in range(len(rows) - 1):
        for i in range(count):
            quad = (j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i)
            faces.append(quad if sign < 0 else quad[::-1])
    b.add(verts, faces, tile)
    soffit = [(-a, sign * bb, z - .02), (a, sign * bb, z - .02), (a, 0, z + rise - .06), (-a, 0, z + rise - .06)]
    b.add(soffit, [(0, 1, 2, 3) if sign > 0 else (3, 2, 1, 0)], tile)


def tile_gable(b, w, d, z, rise, overhang, tile, ridge, wood, plaster, seed=2):
    rng = random.Random(seed)
    a, bb = w / 2 + overhang, d / 2 + overhang
    for sign in (-1, 1):
        tile_slope(b, w, d, z, rise, overhang, sign, tile, rng)
        b.box((2 * a + .04, .05, .09), (0, sign * bb, z - .02), wood)          # eave fascia board
    b.tube([(-a - .02, 0, z + rise + .045), (a + .02, 0, z + rise + .045)], .105, ridge, sides=10)
    for i in range(0, int(2 * a / .22)):
        x = -a + .1 + i * .22
        b.ellipsoid((x, 0, z + rise + .10), (.06, .11, .035), ridge, rings=4, sides=8)
    pitch = rise / bb
    for sign in (-1, 1):  # gable-end triangles and barge boards
        x = sign * (w / 2 - .02)
        h = rise * (d / 2) / bb
        b.prism([(x - .14 * sign, -d / 2, z - .04), (x - .14 * sign, d / 2, z - .04), (x - .14 * sign, 0, z + h)],
                [(x + .14 * sign, -d / 2, z - .04), (x + .14 * sign, d / 2, z - .04), (x + .14 * sign, 0, z + h)],
                plaster)
        for s2 in (-1, 1):
            b.tube([(sign * (a + .02), s2 * bb, z - .02), (sign * (a + .02), 0, z + rise + .01)], .035, wood, sides=6)
