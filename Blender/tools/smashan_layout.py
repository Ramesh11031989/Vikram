"""Positions and heights for SET_Smashan (no Blender needed).

Local map in metres: +X east, +Y north (into the cremation ground), +Z up.
Origin is the centre of the entrance path on the ground line of the gate posts' south side.
The set is not placed on the town/palace map yet, because the story gives no route to the cremation ground.
"""

import math

VIKRAM_HEIGHT = 1.84
BETAL_HEIGHT = 1.75

PATH_X, PATH_HALF = 0.0, 1.2
PATH_Y = (-9.0, 8.0)
GATE_Y, GATE_POST_X = -6.0, 1.5
WALL_BOX = (-12.0, 12.0, -6.0, 16.0)  # x0, x1, y0, y1 of the low boundary wall

HORSE_POSTS = ((-3.2, -8.5), (-5.2, -8.5))
HORSE_RAIL_Z = 1.1
HORSE_MARK = (-4.2, -9.4, 0.0)

TRUNK = (4.5, 4.5)


def unit(x, y):
    length = math.hypot(x, y)
    return (x / length, y / length)


# Each profile row: (distance along the limb from the trunk centre, centre-line z, radius)
LOW_DIR = unit(-.876, -.482)
LOW_PROFILE = [(0.0, .78, .30), (.8, .88, .22), (1.6, .92, .18), (2.4, .98, .15), (3.0, 1.05, .12)]
LOW_SEAT_RANGE = (1.0, 3.0)  # stretch of the branch used as a seat and as the hand-over point
LOW_TOP_LIMITS = (1.0, 1.25)

UP_DIR = unit(-.95, .30)
UP_PROFILE = [(0.0, 1.75, .25), (1.0, 1.95, .20), (2.0, 2.10, .15), (3.0, 2.20, .10)]

CLOTH_S = 2.6
CLOTH_WIDTH = 1.1
CLOTH_HEM_Z = .02
HEEL_GAP = .22  # heels stand this far behind the cloth plane (towards +X, away from the path)
HEEL_HALF_SPACING = .10
HEEL_Z = .05
CLOTH_FRAMES = dict(start=1, lift_begin=20, lift_full=44, hold_until=70, down=96)

CHABUTRA = dict(center=(2.6, 1.3), size=(2.0, 2.0), height=.45, step_height=.22)
CHABUTRA_TOP_LIMITS = (.40, .55)
VIKRAM_CARRY_MARK = (1.15, 2.95, 0.0)

ROOT_DIR = unit(-.196, -.98)
ROOT_PROFILE = [(0.0, .40, .45), (.6, .30, .26), (1.0, .24, .22), (1.5, .22, .21), (1.8, .21, .20), (2.4, .12, .15)]
ROOT_SEAT_S = (1.0, 1.8)
ROOT_TOP_LIMITS = (.35, .50)

PYRES = ((-6.0, 7.0, True), (-7.2, 11.0, False))  # x, y, has logs
MEMORIALS = ((-9.0, 2.0), (-9.8, 3.2), (8.0, 12.0), (9.1, 9.5))

FRAME_START, FRAME_END = 1, 96


def profile(table, s):
    """(z, radius) of a limb profile at distance s (linear between rows)."""
    s = max(table[0][0], min(table[-1][0], s))
    for (s0, z0, r0), (s1, z1, r1) in zip(table, table[1:]):
        if s <= s1:
            t = (s - s0) / (s1 - s0)
            return z0 + (z1 - z0) * t, r0 + (r1 - r0) * t
    return table[-1][1], table[-1][2]


def along(direction, s, z=0.0):
    return (TRUNK[0] + direction[0] * s, TRUNK[1] + direction[1] * s, z)


def low_top(s):
    z, r = profile(LOW_PROFILE, s)
    return z + r


def root_top(s):
    z, r = profile(ROOT_PROFILE, s)
    return z + r


def low_tip():
    return along(LOW_DIR, LOW_PROFILE[-1][0], low_top(LOW_PROFILE[-1][0]))


def cloth_origin():
    """Centre of the cloth on the ground (x, y)."""
    x, y, _ = along(UP_DIR, CLOTH_S)
    return x, y


def cloth_top_z():
    z, r = profile(UP_PROFILE, CLOTH_S)
    return z - r + .02


def heels():
    x, y = cloth_origin()
    return [(x + HEEL_GAP, y - HEEL_HALF_SPACING, HEEL_Z), (x + HEEL_GAP, y + HEEL_HALF_SPACING, HEEL_Z)]


def root_seat_centre():
    s = sum(ROOT_SEAT_S) / 2
    x, y, _ = along(ROOT_DIR, s)
    return x, y, root_top(s)


def chabutra_box():
    (cx, cy), (sx, sy) = CHABUTRA['center'], CHABUTRA['size']
    return cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
