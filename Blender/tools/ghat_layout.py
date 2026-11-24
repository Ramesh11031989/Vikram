"""Shared layout numbers for the ghat set (नदी, घाट और फाटक). Pure Python, no Blender needed.

World units are metres, X east, Y north, Z up. Z = 0 is the ghat's top quay and the
origin is the top step centre. Positions agree with `map_anchors` in SET_Palace_Manifest.json.
"""

import math

WATER_Z = -1.4            # night water: same as the palace evening frame (3 dry treads)
STEP_COUNT, STEP_DROP, STEP_DEPTH, STEP_HALF_WIDTH = 8, .40, .45, 6.0
RIVER_WIDTH = 26.0
BED_Z = -3.8
BANK_Y = -1.3             # quay edge, straight past the ghat, bending away east and west
PLINTH_TOP = .30          # chowki platform height above the quay

WALL_TOP, WALL_THICK = .75, .5                    # low riverside wall
GATE_X, GATE_Y = -21.0, -1.0                      # manifest: Ghat | lifting gate (GUESS)
GATE_POST_X = (-22.45, -19.55)
GATE_GRILLE_Y, GATE_GRILLE_BOTTOM, GATE_GRILLE_TOP = -1.2, .05, 2.6
GATE_RAISE = 2.6
GATE_RAISE_FRAMES = (150, 210)                    # after the night testimony; no gate motion in 1-120

LAMP = (-18.6, .40, 2.10)                         # manifest: Ghat | chowki lamp (GUESS)
LAMP_SPOT_DEG, LAMP_SPOT_BLEND = 60.0, .5         # full cone angle of the lamp's light
PERSON = (-18.15, 1.20, PLINTH_TOP)               # stands on the chowki platform, beside the lamp
PERSON_FACING_DEG = 150.0                         # angle from +X; faces north-west, back turned oblique to the river
CLOTH_LOCAL = (.13, -.09, 1.52)                   # red cloth on the rear shoulder, person-local (+Y = facing)


def person_world(local):
    """Person-local (x right, y facing, z up) to world metres."""
    angle = math.radians(PERSON_FACING_DEG - 90.0)
    x, y, z = local
    return (PERSON[0] + x * math.cos(angle) - y * math.sin(angle),
            PERSON[1] + x * math.sin(angle) + y * math.cos(angle),
            PERSON[2] + z)

# Boat route, upstream (east) to downstream (west), then the keyed stops (frame, route index).
BOAT_ROUTE = [(-6.0, -8.0), (-11.0, -8.3), (-16.5, -8.6), (-21.0, -9.6),
              (-26.0, -11.8), (-31.0, -14.5), (-40.0, -19.0)]
BOAT_KEYS = [(1, 2), (36, 2), (96, 3), (120, 4), (180, 5)]
YAW_TURN_FRAMES, YAW_TURN_DEG = (36, 90), 85.0    # the boat swings downstream (west)
SEAT_EYE = (.10, -.30, 1.20)                      # Gopal's seated eye, boat-local (origin at water level)
EYE_PITCH_DEG = 11.0
AIM_TARGET = (-18.4, .8)                          # midway between the lamp and the person
FRAME_START, FRAME_END = 1, 240


def bank_y(x):
    """Near (ghat) bank: straight through the ghat, bending south at the east and north at the west."""
    if x > 16:
        return BANK_Y - ((x - 16) / 60.0) ** 2 * 40.0
    if x < -34:
        return BANK_Y + ((-34 - x) / 60.0) ** 2 * 10.0
    return BANK_Y


def tread_z(step):
    return -STEP_DROP * step


def dry_treads(water_z=WATER_Z):
    return [i for i in range(1, STEP_COUNT + 1) if tread_z(i) > water_z]


def yaw_for(boat_xy, target_xy, eye=SEAT_EYE):
    """Boat yaw (radians; forward = (-sin, cos)) that points the seated eye at target_xy."""
    theta = 0.0
    for _ in range(8):
        ex = boat_xy[0] + eye[0] * math.cos(theta) - eye[1] * math.sin(theta)
        ey = boat_xy[1] + eye[0] * math.sin(theta) + eye[1] * math.cos(theta)
        theta = math.atan2(-(target_xy[0] - ex), target_xy[1] - ey)
    return theta


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def boat_xy(frame):
    keys = BOAT_KEYS
    if frame <= keys[0][0]:
        return BOAT_ROUTE[keys[0][1]]
    for (f0, i0), (f1, i1) in zip(keys, keys[1:]):
        if frame <= f1:
            t = smooth((frame - f0) / (f1 - f0))
            a, b = BOAT_ROUTE[i0], BOAT_ROUTE[i1]
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return BOAT_ROUTE[keys[-1][1]]


def boat_yaw(frame):
    start = yaw_for(BOAT_ROUTE[BOAT_KEYS[0][1]], AIM_TARGET)
    f0, f1 = YAW_TURN_FRAMES
    return start + math.radians(YAW_TURN_DEG) * smooth((frame - f0) / (f1 - f0))
