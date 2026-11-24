"""Detailed banyan for SET_Smashan: fluted trunk, buttress roots, aerial-root curtains and leaf canopy.

The three story limbs (low climbing branch, upper branch, exposed root seat) stay in smashan_story
with their profiles; this module adds bark detail, roots and foliage around them.
"""

import math
import random

from mathutils import Vector

import ghat_kit as k
import smashan_layout as L
import story_kit as SK


def extra_materials(m):
    m['leaf_light'] = k.material('Smashan | banyan young leaf', (.11, .22, .06), .7)
    m['leaf_dark'] = k.material('Smashan | banyan old leaf', (.035, .09, .03), .75)
    m['moss'] = k.material('Smashan | moss', (.06, .13, .04), .95)
    return m


def trunk_detail(m):
    """Vertical bark ridges, knots and a fused-root skirt around the trunk."""
    rng = random.Random(5)
    tx, ty = L.TRUNK
    b = SK.MeshBuilder()
    for i in range(18):  # ridges
        a = math.tau * i / 18 + rng.uniform(-.1, .1)
        r0 = .60 + rng.uniform(0, .05)
        pts = [(math.cos(a + .08 * z) * (r0 - .07 * z), math.sin(a + .08 * z) * (r0 - .07 * z), .2 + z * 1.2)
               for z in (0, .5, 1.0, 1.6, 2.2)]
        b.tube(pts, lambda t: .05 * (1 - .7 * t), m['root'], sides=6)
    for i in range(5):  # knots
        a, z = rng.uniform(0, math.tau), rng.uniform(.8, 2.6)
        r = .5 - .05 * z
        b.ellipsoid((math.cos(a) * r, math.sin(a) * r, z), (.1, .1, .08), m['bark'], rings=5, sides=8)
    for i in range(7):  # moss patches on the damp north side
        a = rng.uniform(1.0, 2.2)
        z = rng.uniform(.2, .9)
        b.ellipsoid((math.cos(a) * .6, math.sin(a) * .6, z), (.14, .05, .12), m['moss'], rings=4, sides=8, rot=(0, 0, a))
    return b.build('Banyan | trunk bark detail', k._current, location=(tx, ty, 0))


def root_web(m):
    """Long surface roots that snake out from the trunk, forked and tapering into the soil."""
    rng = random.Random(23)
    tx, ty = L.TRUNK
    b = SK.MeshBuilder()
    for i in range(9):
        a = rng.uniform(-1.3, 1.6)  # east and north side, clear of the story spots
        d = Vector((math.cos(a), math.sin(a), 0))
        length = rng.uniform(1.6, 3.0)
        pts = []
        for s in range(7):
            f = s / 6
            wob = rng.uniform(-.1, .1)
            side = Vector((-d.y, d.x, 0))
            pts.append(tuple(d * (.4 + length * f) + side * (wob + .18 * math.sin(f * 5 + i)) +
                             Vector((0, 0, .38 * (1 - f) ** 1.6 + .01))))
        b.tube(pts, lambda t: .17 * (1 - .8 * t), m['root'], sides=8)
        if rng.random() < .6:  # fork
            f0 = Vector(pts[3])
            e = f0 + (Vector((-d.y, d.x, 0)) * rng.choice((-1, 1)) + d) * .8
            b.tube([tuple(f0), tuple((f0 + e) / 2 + Vector((0, 0, .06))), (e.x, e.y, .0)],
                   lambda t: .06 * (1 - .8 * t), m['root'], sides=6)
    return b.build('Banyan | surface root web', k._current, location=(tx, ty, 0))


def aerial_curtain(m):
    """Hanging aerial roots in ropy bundles, some reaching the ground and thickening into pillars."""
    rng = random.Random(41)
    b = SK.MeshBuilder()
    for i in range(16):
        s = .6 + i * .17
        if abs(s - L.CLOTH_S) < .75 or s > 2.9:
            continue
        x, y, _ = L.along(L.UP_DIR, s)
        z = L.profile(L.UP_PROFILE, s)[0] - .1
        for j in range(3):
            ox, oy = rng.uniform(-.06, .06), rng.uniform(-.06, .06)
            low = rng.choice((1.3, 1.6, 2.0, .8)) if i % 4 else 0.0
            pts = [(x + ox + .03 * math.sin(f * 4 + j), y + oy, z - (z - low) * f) for f in (0, .25, .5, .75, 1)]
            b.tube(pts, lambda t: .03 * (1 - .5 * t) if low else .02 * (1 - .6 * t), m['root'], sides=5)
    return b.build('Banyan | aerial root curtain', k._current)


def canopy(m):
    """Broad crown: many overlapping leaf-cluster blobs in three greens, over side limbs and twigs."""
    rng = random.Random(77)
    tx, ty = L.TRUNK
    bark = SK.MeshBuilder()
    leaves = SK.MeshBuilder()
    mats = (m['leaf'], m['leaf_light'], m['leaf_dark'])
    heads = []
    for i in range(7):
        a = math.tau * i / 7 + rng.uniform(-.3, .3)
        out = Vector((math.cos(a), math.sin(a), 0))
        start = Vector((-.2, .15, 3.1))
        pts = SK.spline([tuple(start), tuple(start + out * 1.1 + Vector((0, 0, .5))),
                         tuple(start + out * 2.3 + Vector((0, 0, .9 + rng.uniform(0, .5)))),
                         tuple(start + out * rng.uniform(3.2, 4.0) + Vector((0, 0, 1.2 + rng.uniform(0, .6))))], 6)
        bark.tube(pts, lambda t: .17 * (1 - .8 * t), m['bark'], sides=8)
        for p in pts[len(pts) // 2:]:
            heads.append(Vector(p))
    for h in heads:
        for _ in range(5):
            c = h + Vector((rng.gauss(0, .55), rng.gauss(0, .55), rng.gauss(.15, .35)))
            r = rng.uniform(.4, .85)
            leaves.ellipsoid(tuple(c), (r, r * rng.uniform(.8, 1.1), r * .5), rng.choice(mats),
                             rot=(rng.uniform(-.4, .4), rng.uniform(-.4, .4), rng.uniform(0, 3)), rings=5, sides=9)
    bark.build('Banyan | crown limbs', k._current, location=(tx, ty, 0))
    return leaves.build('Banyan | crown leaves', k._current, location=(tx, ty, 0))


def banyan_detail(m):
    extra_materials(m)
    trunk_detail(m)
    root_web(m)
    aerial_curtain(m)
    canopy(m)
