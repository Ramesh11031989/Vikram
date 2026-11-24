"""Window and door fittings for the town wall modules, built in the house root's local space.

`axis` 'x': the wall runs along local x at y = fixed.  'y': along local y at x = fixed.
`side` is +1/-1: which face of the wall is the street side.
"""

import math

import town_layout as T


def P(axis, along, fixed, a, off, z):
    """Point `a` along the wall from the bay centre and `off` out from the wall plane."""
    return (along + a, fixed + off, z) if axis == 'x' else (fixed + off, along + a, z)


def S(axis, length, thick, height):
    """Box size for a part `length` along the wall and `thick` through it."""
    return (length, thick, height) if axis == 'x' else (thick, length, height)


def window(b, axis, along, fixed, z0, m, side, rng):
    w, hgt, sill = T.WINDOW_W, T.WINDOW_H, T.WINDOW_SILL
    zc = z0 + sill + hgt / 2
    wood = m['wood']
    for sgn in (-1, 1):
        b.box(S(axis, .07, .075, hgt + .14), P(axis, along, fixed, sgn * (w / 2 + .01), side * .02, zc), wood)
    b.box(S(axis, w + .24, .075, .08), P(axis, along, fixed, 0, side * .02, z0 + sill + hgt + .06), wood)
    b.box(S(axis, w + .30, .16, .06), P(axis, along, fixed, 0, side * .055, z0 + sill - .02), m['stone'])
    b.box(S(axis, w + .50, .105, .13), P(axis, along, fixed, 0, side * .03, z0 + sill + hgt + .16), wood)
    b.box(S(axis, w - .06, .004, hgt - .06), P(axis, along, fixed, 0, -side * .03, zc), m['dark'])
    for i in (-1, 0, 1):
        b.tube([P(axis, along, fixed, i * w / 4, 0, z0 + sill + .01),
                P(axis, along, fixed, i * w / 4, 0, z0 + sill + hgt - .01)], .014, wood, sides=8)
    b.box(S(axis, w, .012, .05), P(axis, along, fixed, 0, 0, zc), wood)
    for sgn in (-1, 1):  # two shutter leaves hung on the jambs, one ajar
        ang = math.radians(rng.choice((14, 28, 62))) if sgn == 1 else math.radians(8)
        hinge, leaf = sgn * (w / 2 + .09), w / 2 + .01
        swing = 1 if sgn == 1 else .2
        for plank in range(4):
            off = (plank + .5) * leaf / 4
            b.box(S(axis, leaf / 4 - .004, .026, hgt),
                  P(axis, along, fixed, hinge - sgn * off * math.cos(ang),
                    side * (.045 + off * math.sin(ang) * swing), zc), wood)
        for zz in (zc - hgt * .32, zc + hgt * .32):
            b.box(S(axis, leaf * math.cos(ang), .022, .06),
                  P(axis, along, fixed, hinge - sgn * leaf / 2 * math.cos(ang),
                    side * (.065 + leaf / 2 * math.sin(ang) * swing), zz), m['iron'])


def door(b, axis, along, fixed, z0, m, side):
    w, hgt = T.DOOR_W, T.DOOR_H
    wood, iron = m['wood'], m['iron']
    for sgn in (-1, 1):
        b.box(S(axis, .10, .11, hgt + .08), P(axis, along, fixed, sgn * (w / 2 + .03), side * .02, z0 + hgt / 2), wood)
    b.box(S(axis, w + .30, .12, .10), P(axis, along, fixed, 0, side * .02, z0 + hgt + .06), wood)
    b.box(S(axis, w + .70, .13, .16), P(axis, along, fixed, 0, side * .035, z0 + hgt + .20), wood)
    b.box(S(axis, w + .60, .50, .12), P(axis, along, fixed, 0, side * .27, z0 + .06), m['stone'])
    planks = 6
    for i in range(planks):
        a = -w / 2 + .03 + (i + .5) * (w - .06) / planks
        b.box(S(axis, (w - .06) / planks - .008, .05, hgt - .04), P(axis, along, fixed, a, 0, z0 + hgt / 2), wood)
    for zz in (.35, hgt / 2, hgt - .35):
        b.box(S(axis, w - .10, .03, .10), P(axis, along, fixed, 0, side * .045, z0 + zz), m['wood_dark'])
        for j in range(5):
            b.ellipsoid(P(axis, along, fixed, -w / 2 + .12 + j * (w - .24) / 4, side * .063, z0 + zz),
                        (.014, .014, .014), iron, rings=4, sides=8)
    ring = [P(axis, along, fixed, w / 2 - .14 + .05 * math.cos(math.tau * i / 14), side * .075,
              z0 + 1.05 + .05 * math.sin(math.tau * i / 14)) for i in range(15)]
    b.tube(ring, .008, iron, sides=6, cap=False)
    b.box(S(axis, .06, .02, .10), P(axis, along, fixed, w / 2 - .14, side * .06, z0 + 1.10), iron)
