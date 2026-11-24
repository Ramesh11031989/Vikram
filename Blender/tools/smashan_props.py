"""Detailed stonework for SET_Smashan: chabutra, pyres, memorials, boundary wall and gate."""

import math
import random

from mathutils import Vector

import ghat_kit as k
import smashan_layout as L
import story_kit as SK
from town_hard import Hard


def chabutra_detail(m):
    """Lime-washed platform: moulded base, brick courses, chipped cap, two-riser step, niche, offerings."""
    rng = random.Random(8)
    (cx, cy), (sx, sy) = L.CHABUTRA['center'], L.CHABUTRA['size']
    h, step = L.CHABUTRA['height'], L.CHABUTRA['step_height']
    b = Hard()
    b.box((sx + .16, sy + .16, .10), (0, 0, .05), m['stone'])
    b.box((sx + .06, sy + .06, .05), (0, 0, .125), m['chabutra'])
    for i in range(4):
        z = .15 + i * (h - .21) / 4
        for sgn in (-1, 1):
            for n in range(int(sx / .3)):
                x = -sx / 2 + .15 + n * .3 + (.07 if i % 2 else 0)
                b.box((.27, .02, (h - .21) / 4 - .015), (x, sgn * (sy / 2 + .005), z + .04), m['chabutra'])
                b.box((.02, .27, (h - .21) / 4 - .015), (sgn * (sx / 2 + .005), x, z + .04), m['chabutra'])
    b.box((sx + .12, sy + .12, .06), (0, 0, h - .03), m['chabutra'])
    for _ in range(9):
        b.box((rng.uniform(.04, .12), .015, .01), (rng.uniform(-sx / 2, sx / 2) * .9, rng.uniform(-sy / 2, sy / 2) * .9, h + .003),
              m['ash'], yaw=rng.uniform(0, 3))
    b.box((.5, .02, .28), (-sx / 2 - .035, sy * .3, .3), m['ash'])
    b.box((.56, .03, .05), (-sx / 2 - .04, sy * .3, .46), m['stone'])
    obj = b.build('Chabutra | platform', k._current, location=(cx, cy, 0))
    s = Hard()
    s.box((.6, 1.2, step * .5), (0, 0, step * .25), m['chabutra'])
    s.box((.32, 1.2, step), (.14, 0, step / 2), m['chabutra'])
    s.box((.64, 1.26, .03), (0, 0, step + .01), m['stone'])
    s.build('Chabutra | step (path side)', k._current, location=(cx - sx / 2 - .3, cy, 0))
    o = SK.MeshBuilder()
    o.lathe([(0, 0), (.04, .0), (.065, .02), (.07, .035), (.055, .04), (.03, .025)], m['wood'], sides=16)
    o.ellipsoid((.3, .1, .015), (.1, .08, .03), m['mark'], rings=4, sides=8)
    for _ in range(14):
        o.ellipsoid((.3 + rng.gauss(0, .06), .1 + rng.gauss(0, .05), .035), (.025, .025, .015), m['mark'], rings=3, sides=6)
    o.build('Chabutra | offerings', k._current, location=(cx - .5, cy - .3, h))
    return obj


def pyre(x, y, logs, i, m):
    rng = random.Random(100 + i)
    b = SK.MeshBuilder()
    b.ellipsoid((0, 0, .02), (1.3, .75, .03), m['ash'], rings=5, sides=16)
    for _ in range(30):
        b.ellipsoid((rng.uniform(-1.1, 1.1), rng.uniform(-.6, .6), .03), (.07, .05, .02), m['ash'], rings=3, sides=6)
    for _ in range(6):
        a = rng.uniform(0, math.tau)
        b.ellipsoid((math.cos(a) * 1.35, math.sin(a) * .85, .06), (.13, .1, .07), m['stone'], rings=4, sides=8)
    if logs:
        for layer in range(4):
            n = 6 - layer
            for j in range(n):
                along = layer % 2 == 0
                off = (j - (n - 1) / 2) * .2 + rng.uniform(-.02, .02)
                z = .1 + layer * .15
                a = Vector((-1.0, off, z)) if along else Vector((off, -.6, z))
                e = Vector((1.0, off, z + rng.uniform(-.02, .03))) if along else Vector((off, .6, z))
                mid = (a + e) / 2 + Vector((0, 0, rng.uniform(-.02, .02)))
                b.tube([tuple(a), tuple(mid), tuple(e)], lambda t: .085 + .02 * math.sin(math.pi * t), m['wood'], sides=9)
        for _ in range(8):
            b.ellipsoid((rng.choice((-1, 1)) * 1.0, rng.uniform(-.5, .5), .2 + rng.random() * .4), (.07, .08, .08),
                        m['ash'], rings=4, sides=8)
    else:
        for _ in range(7):
            b.tube([(rng.uniform(-.8, .8), rng.uniform(-.4, .4), .04),
                    (rng.uniform(-.8, .8), rng.uniform(-.4, .4), .06)], .045, m['ash'], sides=6)
    return b.build(f'Pyre {i} | ash bed', k._current, location=(x, y, 0))


def memorial(x, y, i, m):
    rng = random.Random(40 + i)
    b = Hard()
    b.box((.62, .62, .08), (0, 0, .04), m['stone'])
    b.box((.5, .5, .2), (0, 0, .18), m['stone'])
    b.box((.54, .54, .04), (0, 0, .30), m['chabutra'])
    b.box((.2, .2, .62), (0, 0, .63), m['stone'])
    b.prism([(-.12, -.12, .94), (.12, -.12, .94), (0, -.12, 1.05)],
            [(-.12, .12, .94), (.12, .12, .94), (0, .12, 1.05)], m['stone'])
    for z in (.5, .56, .62):
        b.box((.22, .22, .012), (0, 0, z), m['ash'])
    b.box((.1, .01, .14), (0, -.105, .76), m['ash'])
    obj = b.build(f'Memorial {i} | upright stone', k._current, location=(x, y, 0))
    obj.rotation_euler.z = rng.uniform(-.2, .2)
    p = SK.MeshBuilder()
    p.lathe([(0, 0), (.05, 0), (.07, .02), (.06, .04), (.03, .03)], m['wood'], sides=14)
    p.ellipsoid((0, 0, .045), (.02, .02, .03), m['mark'], rings=3, sides=6)
    p.build(f'Memorial {i} | plinth lamp', k._current, location=(x + .15, y - .2, .31))
    return obj


def wall_run(name, a, b2, m, seed):
    """Brick wall: staggered courses, a rounded coping and fallen bricks at the foot."""
    rng = random.Random(seed)
    A, B = Vector((*a, 0)), Vector((*b2, 0))
    run = B - A
    length, unit = run.length, run.normalized()
    yaw = math.atan2(unit.y, unit.x)
    b = Hard()
    for c in range(7):
        pos = rng.uniform(0, .15) if c % 2 else 0.0
        while pos < length - .02:
            blk = min(rng.uniform(.28, .4), length - pos)
            mid = A + unit * (pos + blk / 2)
            b.box((blk - .015, .4 + rng.uniform(-.015, .015), .125), (mid.x, mid.y, .065 + c * .13),
                  m['stone'] if rng.random() > .2 else m['chabutra'], yaw=yaw)
            pos += blk
    b.tube([(p.x, p.y, .93) for p in (A + unit * (length * i / 12) for i in range(13))], .24, m['chabutra'], sides=6)
    for _ in range(max(2, int(length / 2.5))):
        p = A + unit * rng.uniform(0, length)
        b.box((.2, .1, .06), (p.x + rng.uniform(-.2, .2), p.y + rng.uniform(.3, .6), .03), m['stone'], yaw=rng.uniform(0, 3))
    return b.build(name, k._current)


def gate_detail(m):
    gx = L.GATE_POST_X
    for side, name in ((-1, 'west'), (1, 'east')):
        b = Hard()
        b.box((.7, .7, .2), (0, 0, .1), m['stone'])
        b.box((.56, .56, 1.9), (0, 0, 1.1), m['stone'])
        for z in (.5, .9, 1.3, 1.7):
            b.box((.585, .585, .03), (0, 0, z), m['chabutra'])
        b.box((.72, .72, .1), (0, 0, 2.17), m['chabutra'])
        b.ellipsoid((0, 0, 2.30), (.3, .3, .2), m['chabutra'], rings=6, sides=14)
        b.tube([(0, 0, 2.48), (0, 0, 2.62)], .035, m['stone'], sides=8)
        b.build(f'Gate | {name} post', k._current, location=(side * gx, L.GATE_Y, 0))
    t = SK.MeshBuilder()
    t.tube([(-gx, 0, 0), (gx, 0, 0)], .12, m['wood'], sides=10)
    t.build('Gate | lintel beam', k._current, location=(0, L.GATE_Y, 2.05))
    g = SK.MeshBuilder()
    for i in range(7):
        x = -gx + .3 + i * (2 * gx - .6) / 6
        g.ellipsoid((x, 0, -.08 * math.sin(math.pi * i / 6)), (.07, .07, .06), m['mark'], rings=4, sides=8)
    g.build('Gate | marigold garland', k._current, location=(0, L.GATE_Y - .1, 1.9))

