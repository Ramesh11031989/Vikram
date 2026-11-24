"""Neem trees, hay heaps and grass tufts for the town set (metres, Z up)."""

import math
import random

from mathutils import Vector

import ghat_kit as k
import story_kit as SK


def neem(name, x, y, seed, m, height=1.0):
    """Flared trunk with roots, a fork into four limbs, secondary twigs and ~45 leaf clusters."""
    rng = random.Random(seed)
    b = SK.MeshBuilder()
    lean = Vector((rng.uniform(-.25, .25), rng.uniform(-.25, .25), 0))
    trunk = SK.spline([(0, 0, 0), tuple(lean * .4 + Vector((0, 0, 1.2))), tuple(lean + Vector((0, 0, 2.4)))], 8)
    b.tube(trunk, lambda t: .30 * (1 - .42 * t) * (1 + .5 * (1 - t) ** 6), m['bark'], sides=14)
    for i in range(6):  # buttress roots
        a = math.tau * i / 6 + rng.uniform(-.3, .3)
        root = SK.spline([(.12 * math.cos(a), .12 * math.sin(a), .35),
                          (.36 * math.cos(a), .36 * math.sin(a), .07),
                          (.75 * math.cos(a), .75 * math.sin(a), -.02)], 5)
        b.tube(root, lambda t: .11 * (1 - .85 * t), m['bark'], sides=8)
    top = Vector(trunk[-1])
    clusters = []
    for i in range(4):
        a = math.tau * i / 4 + rng.uniform(-.4, .4)
        out = Vector((math.cos(a), math.sin(a), 0))
        limb = SK.spline([tuple(top), tuple(top + out * .6 + Vector((0, 0, .6))),
                          tuple(top + out * 1.5 + Vector((0, 0, 1.4 + rng.uniform(0, .5)))),
                          tuple(top + out * 2.4 + Vector((0, 0, 2.1 + rng.uniform(0, .6))))], 7)
        b.tube(limb, lambda t: .15 * (1 - .8 * t), m['bark'], sides=10)
        for j in range(3):  # twigs
            start = Vector(limb[int(len(limb) * (.4 + .2 * j))])
            end = start + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(.5, 1.1)))
            b.tube(SK.spline([tuple(start), tuple((start + end) / 2 + Vector((0, 0, .15))), tuple(end)], 5),
                   lambda t: .045 * (1 - .8 * t), m['bark'], sides=6)
            clusters.append(end)
        clusters.append(Vector(limb[-1]))
    leaf_materials = (m['leaf'], m['leaf_light'])
    for point in clusters:
        for _ in range(4):
            c = point + Vector((rng.gauss(0, .7), rng.gauss(0, .7), rng.gauss(.25, .45)))
            r = rng.uniform(.45, .85)
            b.ellipsoid(tuple(c), (r, r * rng.uniform(.8, 1.1), r * .62), rng.choice(leaf_materials),
                        rot=(rng.uniform(-.3, .3), rng.uniform(-.3, .3), rng.uniform(0, 3)), rings=6, sides=10)
    obj = b.build(name, k._current, location=(x, y, 0))
    obj.scale = (height, height, height)
    return obj


def hay_heap(name, center, size, m, seed=3):
    """Lumpy mound of loose hay: a core ellipsoid plus layered, tilted straw bundles."""
    rng = random.Random(seed)
    b = SK.MeshBuilder()
    b.ellipsoid((0, 0, size[2] * .35), (size[0], size[1], size[2] * .8), m['hay'], rings=10, sides=18)
    for _ in range(26):
        a, h = rng.uniform(0, math.tau), rng.uniform(.05, .75)
        p = Vector((math.cos(a) * size[0] * .8 * (1 - h * .6), math.sin(a) * size[1] * .8 * (1 - h * .6), size[2] * h))
        q = p + Vector((math.cos(a) * rng.uniform(.1, .3), math.sin(a) * rng.uniform(.1, .3), rng.uniform(-.2, .12)))
        b.tube([tuple(p), tuple(q)], .035, m['hay'], sides=5, taper=.7)
    return b.build(name, k._current, location=center)


def grass_tuft(name, location, m, seed, blades=26, height=.35):
    rng = random.Random(seed)
    b = SK.MeshBuilder()
    for _ in range(blades):
        a = rng.uniform(0, math.tau)
        base = Vector((rng.gauss(0, .035), rng.gauss(0, .035), 0))
        tip = base + Vector((math.cos(a) * rng.uniform(.04, .16), math.sin(a) * rng.uniform(.04, .16), height * rng.uniform(.6, 1.1)))
        b.tube([tuple(base), tuple((base + tip) / 2 + Vector((0, 0, .02))), tuple(tip)], .006, m['leaf'], sides=3, taper=.9)
    return b.build(name, k._current, location=location)
