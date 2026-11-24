"""Betal's hut exterior, veranda and yard props for SET_Sharan."""

import math

import ghat_kit as k
import sharan_detail as D
import sharan_layout as L
from smashan_world import collection


def hut(m):
    collection("Sharan | Betal's hut")
    h = L.HUT
    cx, cy, w, d, wall_h, t = h['cx'], h['cy'], h['w'], h['d'], h['wall_h'], h['wall_t']
    F, front, vf = L.hut_floor_z(), L.hut_front_y(), L.veranda_front_y()
    dw, dh = h['door_w'], h['door_h']
    k.box('Hut | platform plinth', (cx, (vf + cy + d / 2 + .1) / 2, L.PLATFORM_Z + L.PLINTH_H / 2 - .02),
          (w + .6, cy + d / 2 + .1 - vf, L.PLINTH_H), m['mud'], bevel=.03)
    k.box('Hut | plinth step', (cx, vf - .2, L.PLATFORM_Z + .075), (1.6, .4, .15), m['stone'], bevel=.02)
    left_w = (w - dw) / 2
    k.box('Hut | south wall left of door', (cx - dw / 2 - left_w / 2, front + t / 2, F + wall_h / 2), (left_w, t, wall_h), m['mud'], bevel=.04)
    k.box('Hut | south wall right of door', (cx + dw / 2 + left_w / 2, front + t / 2, F + wall_h / 2), (left_w, t, wall_h), m['mud'], bevel=.04)
    k.box('Hut | wall above door', (cx, front + t / 2, F + dh + (wall_h - dh) / 2), (dw, t, wall_h - dh), m['mud'], bevel=.03)
    k.box('Hut | north wall', (cx, cy + d / 2 - t / 2, F + wall_h / 2), (w, t, wall_h), m['mud'], bevel=.04)
    for side, name in ((-1, 'west'), (1, 'east')):
        k.box(f'Hut | {name} wall', (cx + side * (w / 2 - t / 2), cy, F + wall_h / 2), (t, d - 2 * t, wall_h), m['mud'], bevel=.04)
        k.box(f'Hut | door frame {name} post', (cx + side * (dw / 2 + .04), front + .06, F + dh / 2), (.08, .12, dh), m['wood'], bevel=.01)
    k.box('Hut | door frame lintel', (cx, front + .06, F + dh + .04), (dw + .2, .12, .08), m['wood'], bevel=.01)
    k.box('Hut | open door leaf (swung back)', (cx + dw / 2 + .12, front - .32, F + dh / 2 - .02), (.05, .62, dh - .06), m['wood'], bevel=.01)
    wx = cx + dw / 2 + left_w / 2  # window with an open shutter, east of the door
    k.box('Hut | window dark opening', (wx, front - .005, F + 1.25), (.42, .02, .42), m['ash'])
    k.box('Hut | window frame top', (wx, front - .015, F + 1.49), (.52, .03, .05), m['wood'])
    k.box('Hut | window frame bottom', (wx, front - .015, F + 1.01), (.52, .03, .05), m['wood'])
    k.box('Hut | window shutter', (wx + .3, front - .09, F + 1.25), (.04, .18, .42), m['wood'], yaw=.5)
    x0, x1 = cx - w / 2 - L.ROOF_OVERHANG[1], cx + w / 2 + L.ROOF_OVERHANG[1]
    yS, yN = cy - d / 2 - L.ROOF_OVERHANG[0], cy + d / 2 + L.ROOF_OVERHANG[0]
    ze, zr = L.eave_z(), L.ridge_z()
    D.hut_roof(m)
    for side, name in ((-1, 'west'), (1, 'east')):
        gx = cx + side * (w / 2 - t / 2)
        gable = k.mesh_object(f'Hut | {name} gable', [(gx, cy - d / 2, F + wall_h), (gx, cy + d / 2, F + wall_h), (gx, cy, zr - .1)],
                              [(0, 1, 2)], m['mud'])
        gable.modifiers.new('Gable thickness', 'SOLIDIFY').thickness = t * .8
    k.box('Hut | dark floor inside', (cx, cy, F + .01), (w - 2 * t, d - 2 * t, .02), m['ash'])
    k.box('Hut | charpai top', (cx, cy + .45, F + .42), (2.0, .8, .05), m['cloth'])
    for i, (sx, sy) in enumerate(((-.95, .1), (.95, .1), (-.95, .8), (.95, .8))):
        k.rod(f'Hut | charpai leg {i + 1}', (cx + sx, cy + sy, F), (cx + sx, cy + sy, F + .42), .035, m['wood'], vertices=6)


def yard(m):
    collection("Sharan | Hut yard props")
    h = L.HUT
    cx, cy, w = h['cx'], h['cy'], h['w']
    F, front, vf = L.hut_floor_z(), L.hut_front_y(), L.veranda_front_y()
    px, py = cx + 1.35, vf + .6
    k.box('Prop | pot stand', (px, py, F + .03), (.34, .34, .06), m['wood'])
    k.sphere('Prop | water pot on veranda', (px, py, F + .26), (.22, .22, .22), m['clay'])
    k.rod('Prop | water pot neck', (px, py, F + .4), (px, py, F + .54), .1, m['clay'], vertices=10)
    for layer in range(3):  # stacked firewood beside the east wall
        for j in range(5 - layer):
            y = cy - .8 + j * .24 + layer * .12
            z = L.PLATFORM_Z + .09 + layer * .16
            k.rod(f'Prop | log {layer + 1}.{j + 1}', (cx + w / 2 + .2, y, z), (cx + w / 2 + 1.2, y, z), .08, m['wood'], vertices=8)
    dx, dy, dz = cx - 2.6, vf - .6, L.PLATFORM_Z  # dhuni fire ring
    k.box('Dhuni | ash bed', (dx, dy, dz + .015), (.9, .9, .03), m['ash'])
    for i in range(8):
        a = math.tau * i / 8
        k.sphere(f'Dhuni | stone {i + 1}', (dx + math.cos(a) * .5, dy + math.sin(a) * .5, dz + .07), (.1, .09, .07), m['stone'])
    k.sphere('Dhuni | glowing embers', (dx, dy, dz + .07), (.22, .22, .08), m['flame'])
    k.rod('Prop | lantern hook', (cx + .85, front - .12, F + 1.95), (cx + .85, front - .12, F + 1.75), .01, m['wood'], vertices=6)
    k.box('Prop | lantern', (cx + .85, front - .12, F + 1.64), (.14, .14, .2), m['flame'])
    k.sphere("Prop | Betal's cloth bundle on a peg", (cx - .75, front - .12, F + 1.4), (.17, .13, .2), m['cloth'])
    k.rod('Prop | bundle peg', (cx - .75, front, F + 1.58), (cx - .75, front - .12, F + 1.58), .015, m['wood'], vertices=6)
    k.empty('MARK | Hut door (Vikram sets Betal down before it)', L.door_centre(), 'ARROWS', .6)
    k.empty('MARK | Vikram sets Betal down on the veranda', L.veranda_mark(), 'ARROWS', .5)
