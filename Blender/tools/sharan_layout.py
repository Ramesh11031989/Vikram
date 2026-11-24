"""Positions, heights and seating plan for SET_Sharan (no Blender needed).

Local map in metres: +X east, +Y north (uphill, away from the cremation ground), +Z up.
Origin is the middle of the flat ground just behind the cremation-ground wall, at the foot of the path.
The story gives no route from the ghat or town, so the set is not placed on the palace map.
"""

import math

VIKRAM_HEIGHT = 1.84
BETAL_HEIGHT = 1.75

X_RANGE = (-24.0, 24.0)
Y_RANGE = (-8.0, 52.0)

# (y, z) keys of the slope; each stretch eases in and out, so terraces stay flat.
PROFILE = [(-8.0, 0.0), (2.0, 0.0), (10.0, 1.5), (21.0, 1.5), (37.0, 4.8), (52.0, 4.8)]
TERRACE_Y = (10.0, 21.0)
PLATFORM_Y = (37.0, 52.0)
PLATFORM_Z = 4.8
SIDE_BANK_FROM_X = 13.0  # the ground rises gently beyond this |x|

PATH_HALF = .75
PATH_Y = (-4.0, 39.3)
PATH_WIGGLE = 3.0
MAX_GRADE_DEG = 20.0

WALL_Y = -4.0  # low wall of the cremation ground, below the slope
WALL_HALF_GAP = 1.4

HUT = dict(cx=-1.0, cy=43.0, w=3.4, d=2.8, wall_h=2.15, wall_t=.28, door_w=1.0, door_h=1.8)
PLINTH_H = .22
VERANDA_DEPTH = 2.0
EAVE_DROP = .12
RIDGE_RISE = .95
ROOF_OVERHANG = (.6, .5)  # front/back, sides

SEAT_CENTRE = (-6.0, 15.0)  # the sailors' writing board
INNER_RING = dict(r=2.4, start=100.0, step=32.0, count=6)  # seats 1-6
OUTER_RING = dict(r=4.8, start=90.0, step=180.0 / 7, count=8)  # seats 7-14
GOPAL_SEAT = 3
HEARING_M = 9.0
SEATED_EYE = .9
OVERFLOW_MATS = ((7.0, 12.0), (8.6, 13.8), (7.4, 16.4), (9.4, 18.0))  # more families, east of the path
BOARD_SIZE = (.6, 1.2, .25)

TREES = ((-16.0, 6.0), (-17.0, 24.0), (15.0, 10.0), (14.0, 26.0), (-8.5, 46.0), (6.5, 45.0), (-14.0, 40.0), (12.0, 38.0))
FRAME_START, FRAME_END = 1, 48


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def base_z(y):
    y = max(PROFILE[0][0], min(PROFILE[-1][0], y))
    for (y0, z0), (y1, z1) in zip(PROFILE, PROFILE[1:]):
        if y <= y1:
            return z0 + (z1 - z0) * smooth((y - y0) / (y1 - y0))
    return PROFILE[-1][1]


def ground_z(x, y):
    edge = max(0.0, abs(x) - SIDE_BANK_FROM_X)
    return base_z(y) + .018 * edge * edge


def path_x(y):
    blend = smooth((y - 28.0) / 9.0)
    return (1 - blend) * PATH_WIGGLE * math.sin(y / 11.0) + blend * HUT['cx']


def path_points(step=.5):
    count = int(round((PATH_Y[1] - PATH_Y[0]) / step))
    ys = [PATH_Y[0] + (PATH_Y[1] - PATH_Y[0]) * i / count for i in range(count + 1)]
    return [(path_x(y), y, ground_z(path_x(y), y)) for y in ys]


def path_dir(y):
    dx, dy = path_x(y + .1) - path_x(y - .1), .2
    length = math.hypot(dx, dy)
    return dx / length, dy / length


def path_grade_deg(y, h=.5):
    """Slope of the path (degrees) between y-h and y+h, measured along its length."""
    a = (path_x(y - h), y - h, ground_z(path_x(y - h), y - h))
    b = (path_x(y + h), y + h, ground_z(path_x(y + h), y + h))
    run = math.hypot(b[0] - a[0], b[1] - a[1])
    return math.degrees(math.atan2(b[2] - a[2], run))


def max_path_grade_deg():
    return max(path_grade_deg(y) for _, y, _ in path_points(1.0)[1:-1])


def path_width():
    return PATH_HALF * 2


def wall_gap_x():
    return path_x(WALL_Y)


# ---- hut ----
def hut_floor_z():
    return PLATFORM_Z + PLINTH_H


def hut_front_y():
    return HUT['cy'] - HUT['d'] / 2


def veranda_front_y():
    return hut_front_y() - VERANDA_DEPTH


def eave_z():
    return hut_floor_z() + HUT['wall_h'] - EAVE_DROP


def ridge_z():
    return hut_floor_z() + HUT['wall_h'] + RIDGE_RISE


def door_centre():
    return HUT['cx'], hut_front_y(), hut_floor_z()


def veranda_mark():
    return HUT['cx'] + .2, veranda_front_y() + 1.0, hut_floor_z()


# ---- seating ----
def _seat(n, r, deg):
    a = math.radians(deg)
    cx, cy = SEAT_CENTRE
    x, y = cx + r * math.cos(a), cy + r * math.sin(a)
    return dict(n=n, x=x, y=y, z=ground_z(x, y), yaw=facing_yaw(x, y, cx, cy), angle=deg, r=r)


def facing_yaw(x, y, tx, ty):
    """Z rotation that turns an object's local +Y towards (tx, ty)."""
    return math.atan2(ty - y, tx - x) - math.pi / 2


def seats():
    out = []
    for i in range(INNER_RING['count']):
        out.append(_seat(i + 1, INNER_RING['r'], INNER_RING['start'] + INNER_RING['step'] * i))
    for j in range(OUTER_RING['count']):
        out.append(_seat(INNER_RING['count'] + j + 1, OUTER_RING['r'], OUTER_RING['start'] + OUTER_RING['step'] * j))
    return out


def gopal():
    return seats()[GOPAL_SEAT - 1]


def mausi():
    g = gopal()
    cx, cy = SEAT_CENTRE
    a = math.radians(g['angle'])
    r = g['r'] - .8
    x, y = cx + r * math.cos(a), cy + r * math.sin(a)
    return dict(x=x, y=y, z=ground_z(x, y), yaw=facing_yaw(x, y, cx, cy))


def overflow_mats():
    out = []
    for x, y in OVERFLOW_MATS:
        out.append(dict(x=x, y=y, z=ground_z(x, y), yaw=facing_yaw(x, y, path_x(y), y)))
    return out


def board_marks():
    cx, cy = SEAT_CENTRE
    z = ground_z(cx, cy)
    return dict(betal=(cx - .85, cy, z), sailor_a=(cx + .85, cy - .4, z), sailor_b=(cx + .85, cy + .4, z))


def nandu_mark():
    return (-.5, 12.0, ground_z(-.5, 12.0))


def seat_label(n):
    if n == GOPAL_SEAT:
        return 'Gopal (third on the list)'
    return 'earlier arrival' if n < GOPAL_SEAT else 'later arrival, can hear Gopal'
