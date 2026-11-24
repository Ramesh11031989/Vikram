"""Detailed wall modules for the town houses: plaster bays with weathering, framed shuttered
windows, panelled studded doors, and a rubble-stone plinth.  Names match the old kit
(`Wall module solid|door|window`, `Plinth`) because validate_town_set.py looks for them."""

import math
import random

from mathutils import Vector

import ghat_kit as k
import town_fittings as F
import town_layout as T
from town_hard import Hard


def wall_bay(root, axis, along, fixed, kind, z0, height, m, plaster, side=-1):
    """One 3 m wall module as two objects: the plaster wall and its timber/iron fittings."""
    rng = random.Random(int(abs(along * 31 + fixed * 17 + z0 * 7)) + 11)
    t, h = T.WALL_T, T.BAY / 2
    if kind == 'door':
        w = T.DOOR_W / 2
        pieces = [(-h, -w, 0, height), (w, h, 0, height), (-w, w, T.DOOR_H, height)]
    elif kind == 'window':
        w, s = T.WINDOW_W / 2, T.WINDOW_SILL
        pieces = [(-h, -w, 0, height), (w, h, 0, height), (-w, w, 0, s), (-w, w, s + T.WINDOW_H, height)]
    else:
        pieces = [(-h, h, 0, height)]
    b = Hard()
    for a0, a1, lo, hi in pieces:
        b.box(F.S(axis, a1 - a0, t, hi - lo), F.P(axis, along, fixed, (a0 + a1) / 2, 0, z0 + (lo + hi) / 2), plaster)
    out = side * (t / 2 + .004)
    if z0 < .5:
        b.box(F.S(axis, T.BAY - .02, .012, .42), F.P(axis, along, fixed, 0, out, z0 + .21), m['damp'])
    for _ in range(3):  # lime-wash patches, kept clear of openings
        pw, ph = rng.uniform(.25, .7), rng.uniform(.2, .6)
        pz, pa = z0 + rng.uniform(.8, max(.9, height - 1.0)), rng.uniform(-h + .4, h - .4)
        if (kind == 'window' and abs(pa) < T.WINDOW_W / 2 + .4) or (kind == 'door' and abs(pa) < T.DOOR_W / 2 + .4):
            continue
        b.box(F.S(axis, pw, .008, ph), F.P(axis, along, fixed, pa, out, pz), m['patch'])
    wall = b.build(f'Wall module {kind}', k._current)
    wall.parent = root
    fit = Hard()
    if kind == 'door':
        F.door(fit, axis, along, fixed, z0, m, side)
    elif kind == 'window':
        F.window(fit, axis, along, fixed, z0, m, side, rng)
    if fit.verts:
        fit.build(f'Wall module {kind} fittings', k._current).parent = root
    return wall


def plinth(root, w, d, m, seed=4):
    """Rubble plinth: three courses of irregular blocks and a drip-stone cap."""
    rng = random.Random(seed)
    b = Hard()
    h, courses = T.PLINTH, 3
    ex, ey = w / 2 + .15, d / 2 + .15
    sides = (((-ex, -ey), (ex, -ey)), ((ex, -ey), (ex, ey)), ((ex, ey), (-ex, ey)), ((-ex, ey), (-ex, -ey)))
    for c in range(courses):
        z0 = h * c / courses
        for (x0, y0), (x1, y1) in sides:
            run = Vector((x1 - x0, y1 - y0, 0))
            unit, length, pos = run.normalized(), run.length, rng.uniform(0, .25)
            while pos < length - .1:
                block = min(rng.uniform(.35, .75), length - pos)
                mid = Vector((x0, y0, 0)) + unit * (pos + block / 2)
                b.box((block - .02, .26 + rng.uniform(0, .03), h / courses - .012),
                      (mid.x, mid.y, z0 + h / courses / 2), m['stone'], yaw=math.atan2(unit.y, unit.x))
                pos += block
    b.box((w + .42, d + .42, .05), (0, 0, h + .015), m['stone'])
    obj = b.build('Plinth', k._current)
    obj.parent = root
    return obj
