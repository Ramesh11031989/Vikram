"""Ghat set terrain: materials, river bend, banks, stone steps and the low riverside wall."""

import math

import ghat_kit as k
import ghat_layout as L

XS = list(range(-90, 91, 6))


def materials():
    return dict(
        stone=k.textured('Ghat | wet dark sandstone', (.085, .080, .074), .55, 5, .5, .35),
        old=k.textured('Ghat | weathered stone', (.13, .115, .095), .8, 3, .5, .4),
        earth=k.textured('Ghat | river-bank earth', (.075, .055, .04), .95, 2.5, .6, .5),
        bed=k.material('Ghat | river bed', (.02, .022, .02), .9),
        water=k.material('Ghat | night water', (.012, .04, .055), .08),
        wood=k.textured('Ghat | boat and gate wood', (.12, .062, .028), .8, 14, .4, .2),
        iron=k.material('Ghat | gate iron', (.018, .02, .024), .45, .8),
        clay=k.material('Ghat | clay lamp', (.30, .12, .05), .9),
        flame=k.material('Ghat | lamp flame', (1, .34, .045), .4, 0, 7),
        red=k.material('Ghat | red shoulder cloth', (.36, .032, .018), .95),
        dark=k.material('Ghat | unidentified person (back only)', (.027, .030, .034), .95),
        route=k.material('Ghat | boat route marker', (.1, .5, .8), .5, 0, 1.2))


def strip(name, pairs, surface):
    verts = [v for pair in pairs for v in pair]
    faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(pairs) - 1)]
    return k.mesh_object(name, verts, faces, surface)


def far_bank_y(x):
    return L.bank_y(x) - L.RIVER_WIDTH - (0.0009 * x * x if x > 0 else 0.0003 * x * x)


def river_and_banks(m):
    k.use(k.collection('Ghat | River bend & banks'))
    near = [(x, L.bank_y(x)) for x in XS]
    far = [(x, far_bank_y(x)) for x in XS]
    strip('River water surface', [((x, y, L.WATER_Z), (fx, fy, L.WATER_Z)) for (x, y), (fx, fy) in zip(near, far)], m['water'])
    strip('River bed', [((x, y, L.BED_Z), (fx, fy, L.BED_Z)) for (x, y), (fx, fy) in zip(near, far)], m['bed'])
    strip('Near quay ground', [((x, y, 0), (x, 34, 0)) for x, y in near], m['old'])
    strip('Near bank face', [((x, y, L.BED_Z), (x, y, 0)) for x, y in near], m['earth'])
    strip('Far bank face', [((fx, fy, .6), (fx, fy, L.BED_Z)) for fx, fy in far], m['earth'])
    strip('Far bank ground', [((fx, fy, .6), (fx, fy - 40, .6)) for fx, fy in far], m['earth'])


def steps_and_quay(m):
    k.use(k.collection('Ghat | Stone steps & quay'))
    depth, half = L.STEP_DEPTH, L.STEP_HALF_WIDTH
    for i in range(1, L.STEP_COUNT + 1):
        top = L.tread_z(i)
        k.box(f'Ghat step {i}', (0, L.BANK_Y - (i - .5) * depth, (top + L.BED_Z) / 2),
              (2 * half, depth, top - L.BED_Z), m['stone'], .015)
        cheek_top = top + .55
        for side in (-1, 1):
            k.box(f'Step cheek wall {i}', (side * (half + .22), L.BANK_Y - (i - .5) * depth, (cheek_top + L.BED_Z) / 2),
                  (.44, depth, cheek_top - L.BED_Z), m['old'], .02)
    for x in (-5.0, 5.0):
        k.box('Quay mooring post', (x, L.BANK_Y + .25, .4), (.28, .28, .8), m['old'], .04)
    k.empty('MARK | Ghat top step centre (map origin)', (0, 0, 0), 'ARROWS', .8)


def wall_segment(a, b, m):
    (x0, y0), (x1, y1) = a, b
    length = math.hypot(x1 - x0, y1 - y0)
    yaw = math.atan2(y1 - y0, x1 - x0)
    mid = ((x0 + x1) / 2, (y0 + y1) / 2)
    k.box('Riverside low wall', (*mid, L.WALL_TOP / 2), (length + .02, L.WALL_THICK, L.WALL_TOP), m['old'], .03, yaw=yaw)
    k.box('Riverside low wall coping', (*mid, L.WALL_TOP + .04), (length + .06, L.WALL_THICK + .12, .09), m['stone'], .02, yaw=yaw)


def wall_run(x_from, x_to, m, step=3.0):
    count = max(1, int(abs(x_to - x_from) // step))
    xs = [x_from + (x_to - x_from) * i / count for i in range(count + 1)]
    offset = L.WALL_THICK / 2 + .05
    for a, b in zip(xs, xs[1:]):
        wall_segment((a, L.bank_y(a) + offset), (b, L.bank_y(b) + offset), m)


def low_wall(m):
    k.use(k.collection('Ghat | Riverside low wall (किनारे की नीची दीवार)'))
    wall_run(-70, L.GATE_POST_X[0] - .3, m)
    wall_run(L.GATE_POST_X[1] + .3, -6.7, m)
    wall_run(6.7, 70, m)
    for x in (-6.45, 6.45):
        k.box('Low wall return at the steps', (x, L.BANK_Y + .1, L.WALL_TOP / 2), (.5, 1.0, L.WALL_TOP), m['old'], .03)
    for x, z in ((-12.0, .45), (-9.5, .52), (12.0, .38)):
        k.box('High-water silt mark', (x, L.BANK_Y + .01, z), (1.2, .02, .05), m['bed'])
