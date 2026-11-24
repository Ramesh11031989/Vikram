"""Detailed hut roof, woven mats, neem trees, rocks and grass for SET_Sharan (reuses the town builders)."""

import math
import random

from mathutils import Vector

import ghat_kit as k
import sharan_layout as L
import story_kit as SK
import town_flora
from town_hard import Hard
from town_roofs import thatch_hip


def extra_materials(m):
    m['leaf_light'] = k.material('Sharan | young neem leaf', (.12, .24, .07), .9)
    m['hay'] = m['thatch']
    m['straw'] = k.material('Sharan | straw', (.55, .44, .20), .95)
    m['rope'] = k.material('Sharan | rope', (.42, .32, .18), .95)
    m['dark'] = k.material('Sharan | dark interior', (.01, .008, .007), 1.)
    return m


def hut_roof(m):
    """Tiered straw hip roof with ridge roll, replacing the two plain slopes."""
    h = L.HUT
    b = Hard()
    thatch_hip(b, h['w'] + .2, h['d'] + .2, L.eave_z() + .12, L.RIDGE_RISE + .1, .55, max(.4, h['w'] - 1.2),
               (m['thatch'], m['wood']), seed=6, tiers=12)
    return b.build('Hut | thatch roof', k._current, location=(h['cx'], h['cy'], 0))


def mat(name, px, py, pz, yaw, m, seed):
    """Woven mat: border strips, weave ribs, frayed fringe and a rolled edge."""
    rng = random.Random(seed)
    b = SK.MeshBuilder()
    w, d = .9, 1.0
    b.box((w, d, .015), (0, 0, .01), m['mat'])
    for i in range(14):
        b.tube([(-w / 2 + .03 + i * (w - .06) / 13, -d / 2 + .02, .02), (-w / 2 + .03 + i * (w - .06) / 13, d / 2 - .02, .02)],
               .008, m['straw'] if i % 3 else m['mat'], sides=4)
    for sgn in (-1, 1):
        b.tube([(sgn * (w / 2 - .02), -d / 2, .03), (sgn * (w / 2 - .02), d / 2, .03)], .014, m['cloth'], sides=6)
        for j in range(12):
            x = -w / 2 + .05 + j * (w - .1) / 11
            b.tube([(x, sgn * d / 2, .012), (x + rng.uniform(-.02, .02), sgn * (d / 2 + rng.uniform(.03, .07)), .006)],
                   .003, m['straw'], sides=3)
    obj = b.build(name, k._current, location=(px, py, pz))
    obj.rotation_euler.z = yaw
    return obj


def tree(i, x, y, z, m, seed):
    obj = town_flora.neem(f'Tree {i} | neem', x, y, seed, m, height=1.15)
    obj.location.z = z
    return obj


def rock(name, loc, size, m, seed):
    rng = random.Random(seed)
    b = SK.MeshBuilder()
    b.ellipsoid((0, 0, 0), size, m['stone'], rings=6, sides=10, rot=(rng.uniform(-.3, .3), 0, rng.uniform(0, 3)))
    for _ in range(3):
        c = (rng.gauss(0, size[0] * .4), rng.gauss(0, size[1] * .4), rng.uniform(0, size[2] * .5))
        b.ellipsoid(c, (size[0] * .45, size[1] * .45, size[2] * .55), m['stone'], rings=4, sides=8)
    return b.build(name, k._current, location=loc)


def grass(name, loc, m, seed):
    return town_flora.grass_tuft(name, loc, {'leaf': m['grass']}, seed, blades=30, height=.42)


def bundle(name, loc, m, seed):
    """Cloth bundle: knotted wrap, loose ends and a tie."""
    rng = random.Random(seed)
    b = SK.MeshBuilder()
    b.ellipsoid((0, 0, .1), (.24, .18, .12), m['cloth'], rings=7, sides=12)
    b.ellipsoid((.05, .02, .2), (.14, .11, .08), m['cloth'], rings=5, sides=10)
    for s in (-1, 1):
        b.tube(SK.spline([(0, 0, .26), (s * .08, .02, .30), (s * .14, .05, .22)], 4), .018, m['cloth'], sides=6)
    b.tube([(-.2, -.02, .13), (0, .17, .15), (.2, -.02, .13)], .009, m['rope'], sides=5)
    obj = b.build(name, k._current, location=loc)
    obj.rotation_euler.z = rng.uniform(0, 3)
    return obj
