"""Shaped props for the town set: clay pots, grain sacks, kadhai, jalebi tray, trough, wheat heap."""

import math
import random

from mathutils import Vector

import ghat_kit as k
import story_kit as SK

POT = [(.0, 0), (.10, .005), (.17, .05), (.225, .14), (.245, .24), (.225, .34), (.17, .41),
       (.105, .455), (.092, .50), (.105, .535), (.122, .548), (.105, .556)]  # matka, radius 0.245 at 0.24 m


def _scaled(profile, factor):
    return [(r * factor, z * factor) for r, z in profile]


def pot(name, center, factor, m, band=True):
    """Round-bellied clay matka with a turned rim, a darker shoulder band and a base ring."""
    b = SK.MeshBuilder()
    b.lathe(_scaled(POT, factor), m['clay_pot'], sides=40, closed_bottom=True)
    if band:
        for z, r in ((.30, .205), (.325, .196)):
            ring = [(r * factor * math.cos(math.tau * i / 40), r * factor * math.sin(math.tau * i / 40), z * factor)
                    for i in range(41)]
            b.tube(ring, .007 * factor, m['clay_dark'], sides=6, cap=False)
    return b.build(name, k._current, location=center)


def oil_jar(name, center, m):
    """Tall glazed storage jar with a flared mouth and two loop handles."""
    b = SK.MeshBuilder()
    b.lathe([(.0, 0), (.15, .0), (.20, .06), (.26, .24), (.27, .42), (.22, .62), (.15, .74), (.13, .80),
             (.17, .85), (.18, .875), (.14, .88)], m['clay_glaze'], sides=40)
    for s in (-1, 1):
        b.tube(SK.spline([(s * .245, 0, .62), (s * .33, 0, .66), (s * .34, 0, .52), (s * .27, 0, .46)], 5),
               .018, m['clay_glaze'], sides=8)
    return b.build(name, k._current, location=center)


def sack(name, center, m, seed, standing=True):
    """Hessian grain sack: a lofted body pinched at a tied neck, with a rope turn and creases."""
    rng = random.Random(seed)
    b = SK.MeshBuilder()
    w, h = .27 + rng.uniform(-.02, .03), .62 + rng.uniform(-.04, .05)
    stations = [((0, 0, .0), w * .70, w * .52), ((0, 0, .06), w * .98, w * .72), ((0, 0, .22), w * 1.05, w * .78),
                ((0, 0, h * .55), w * .98, w * .72), ((0, 0, h * .78), w * .60, w * .44),
                ((0, 0, h * .88), w * .20, w * .17), ((0, 0, h * .95), w * .30, w * .26), ((0, 0, h), w * .12, w * .10)]
    b.loft(stations, m['sack'], sides=22)
    for z in (h * .86,):
        ring = [(w * .20 * math.cos(math.tau * i / 14), w * .17 * math.sin(math.tau * i / 14), z) for i in range(15)]
        b.tube(ring, .009, m['rope'], sides=6, cap=False)
    for i in range(5):  # slumped crease folds
        a = rng.uniform(0, math.tau)
        p = Vector((math.cos(a) * w * .98, math.sin(a) * w * .74, .12))
        q = Vector((math.cos(a) * w * .86, math.sin(a) * w * .66, h * .62))
        b.tube([tuple(p), tuple(q)], .006, m['sack_dark'], sides=4, taper=.4)
    obj = b.build(name, k._current, location=center)
    obj.rotation_euler = (0 if standing else math.radians(rng.choice((78, 84, 90))), 0, rng.uniform(0, math.tau))
    return obj


def wheat_heap(name, center, m, seed=5):
    rng = random.Random(seed)
    b = SK.MeshBuilder()
    b.ellipsoid((0, 0, .15), (1.1, .95, .45), m['grain'], rings=12, sides=24)
    for _ in range(80):
        a, r = rng.uniform(0, math.tau), rng.uniform(.2, 1.0)
        z = .5 * (1 - r ** 2) ** .5
        b.ellipsoid((math.cos(a) * r, math.sin(a) * r * .88, z + .02), (.07, .06, .04), m['grain_dark'], rings=4, sides=6)
    return b.build(name, k._current, location=center)


def kadhai(name, center, m):
    """Wide iron frying pan with a rolled rim, two loop handles, oil, and a heap of jalebi rings."""
    b = SK.MeshBuilder()
    b.lathe([(.0, .0), (.11, .008), (.21, .04), (.30, .09), (.345, .14), (.36, .165), (.352, .17),
             (.335, .15), (.28, .09), (.20, .045), (.10, .015), (.0, .01)], m['soot'], sides=40)
    b.lathe([(.0, .083), (.30, .083)], m['oil'], sides=40, closed_bottom=False)
    for s in (-1, 1):
        b.tube(SK.spline([(s * .35, 0, .15), (s * .43, 0, .17), (s * .46, 0, .12), (s * .38, 0, .115)], 5),
               .014, m['soot'], sides=8)
    return b.build(name, k._current, location=center)


def jalebi_tray(name, center, m, seed=2):
    """Beaten-brass tray with a raised rim holding spiral jalebi coils."""
    rng = random.Random(seed)
    b = SK.MeshBuilder()
    b.lathe([(.0, .0), (.30, .0), (.34, .012), (.36, .045), (.35, .05), (.30, .018), (.0, .016)], m['brass'], sides=44)
    for ring in range(12):
        a, r = rng.uniform(0, math.tau), rng.uniform(.0, .24)
        cx, cy, layer = math.cos(a) * r, math.sin(a) * r, 0 if r > .1 else 1
        coil = [(cx + (.018 + .0058 * t) * math.cos(t * 1.9 + a), cy + (.018 + .0058 * t) * math.sin(t * 1.9 + a),
                 .028 + layer * .016) for t in [i * .45 for i in range(26)]]
        b.tube(coil, .0075, m['jalebi'], sides=6)
    return b.build(name, k._current, location=center)


def trough(name, center, size, m):
    """Hollowed log trough: thick-walled box with chamfered rim, end blocks and fodder inside."""
    w, d, h = size
    b = SK.MeshBuilder()
    t = .06
    b.box((w, t, h), (0, -d / 2 + t / 2, h / 2), m['wood'])
    b.box((w, t, h), (0, d / 2 - t / 2, h / 2), m['wood'])
    b.box((t * 1.4, d, h), (-w / 2 + t * .7, 0, h / 2), m['wood'])
    b.box((t * 1.4, d, h), (w / 2 - t * .7, 0, h / 2), m['wood'])
    b.box((w - t * 2, d - t * 2, .05), (0, 0, .025), m['wood'])
    b.box((w - t * 3, d - t * 3, .04), (0, 0, h * .52), m['hay'])
    for x in (-w * .36, w * .36):
        b.box((.10, d + .08, .07), (x, 0, -.02), m['wood'])
    return b.build(name, k._current, location=center)
