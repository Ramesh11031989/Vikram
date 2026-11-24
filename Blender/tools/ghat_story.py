"""Ghat set story props: lifting gate, chowki, lamp place, unidentified person and the boat."""

import math

import bpy

import ghat_kit as k
import ghat_layout as L


def gate(m):
    k.use(k.collection('Ghat | Lifting gate (उठने वाला फाटक)'))
    p0, p1 = L.GATE_POST_X
    mid = (p0 + p1) / 2
    for x in (p0, p1):
        k.box('Gate stone post', (x, L.GATE_Y, 2.9), (.5, .62, 5.8), m['stone'], .04)
        k.box('Gate post plinth', (x, L.GATE_Y, .2), (.7, .8, .4), m['old'], .03)
        k.box('Windlass bearing block', (x, L.GATE_Y - .1, 5.95), (.3, .3, .3), m['wood'], .02)
    k.box('Gate head beam', (mid, L.GATE_Y, 5.55), (p1 - p0 + .5, .62, .5), m['stone'], .04)
    k.rod('Gate windlass roller', (p0 - .2, L.GATE_Y - .1, 6.15), (p1 + .2, L.GATE_Y - .1, 6.15), .11, m['wood'])
    k.rod('Windlass handle', (p1 + .2, L.GATE_Y - .1, 6.15), (p1 + .2, L.GATE_Y - .1, 6.9), .035, m['wood'])
    root = k.empty('Gate | grille root (rises after frame 150)', (0, L.GATE_GRILLE_Y - L.GATE_Y, 0), 'PLAIN_AXES', .6)
    root.location = (0, 0, 0)
    inner0, inner1 = p0 + .3, p1 - .3
    height = L.GATE_GRILLE_TOP - L.GATE_GRILLE_BOTTOM
    centre_z = (L.GATE_GRILLE_BOTTOM + L.GATE_GRILLE_TOP) / 2
    parts = []
    for i in range(11):
        x = inner0 + (inner1 - inner0) * i / 10
        parts.append(k.box('Gate grille upright', (x, L.GATE_Y, centre_z), (.05, .08, height), m['iron']))
    for z in (.35, 1.3, 2.4):
        parts.append(k.box('Gate grille rail', (mid, L.GATE_Y, z), (inner1 - inner0 + .1, .1, .09), m['wood'], .01))
    for x in (inner0 - .02, inner1 + .02):
        parts.append(k.box('Gate grille stile', (x, L.GATE_Y, centre_z), (.1, .12, height), m['wood'], .01))
    for part in parts:
        part.parent = root
    first, last = L.GATE_RAISE_FRAMES
    for frame, lift in ((1, 0), (first - 1, 0), (last, L.GATE_RAISE), (L.FRAME_END, L.GATE_RAISE)):
        root.location.z = lift
        root.keyframe_insert('location', index=2, frame=frame)
    k.empty('MARK | Gate — lifting gate position (फाटक)', (L.GATE_X, L.GATE_Y, 0), 'CUBE', .5)


def chowki_and_lamp(m):
    k.use(k.collection('Ghat | Chowki & lamp place (चौकी, दीये की जगह)'))
    k.box('Chowki stone platform', (-17.0, 1.0, L.PLINTH_TOP / 2), (4.2, 3.4, L.PLINTH_TOP), m['old'], .03)
    for x in (-18.95, -15.1):
        k.box('Chowki rear post', (x, 2.5, 1.65), (.2, .2, 2.7), m['wood'], .02)
    k.box('Chowki rear wall', (-17.0, 2.7, 1.0), (4.0, .2, 1.4), m['old'], .03)
    k.box('Chowki thatched shade', (-17.0, 1.6, 3.1), (4.6, 3.8, .12), m['wood'], .02)
    lx, ly, lz = L.LAMP
    k.box('Lamp pillar', (lx, ly, (L.PLINTH_TOP + lz - .15) / 2), (.34, .34, lz - .15 - L.PLINTH_TOP), m['stone'], .02)
    k.box('Lamp ledge', (lx, ly, lz - .1), (.62, .5, .1), m['stone'], .02)
    k.sphere('Clay lamp bowl', (lx, ly, lz - .06), (.11, .075, .04), m['clay'])
    k.sphere('Lamp flame', (lx, ly, lz + .01), (.017, .017, .05), m['flame'])
    data = bpy.data.lights.new('Lamp spot (lights the person, not the gate)', 'SPOT')
    data.energy, data.color, data.shadow_soft_size = 28, (1, .40, .10), .02
    data.spot_size, data.spot_blend = math.radians(L.LAMP_SPOT_DEG), L.LAMP_SPOT_BLEND
    spot = bpy.data.objects.new(data.name, data)
    k._current.objects.link(spot)
    spot.location = (lx, ly, lz + .03)
    k.aim(spot, L.person_world(L.CLOTH_LOCAL))


def person(m):
    k.use(k.collection('Ghat | Unidentified person (back only)'))
    yaw = math.radians(L.PERSON_FACING_DEG - 90.0)
    pw = L.person_world

    def part(name, local, scale):
        obj = k.sphere(name, pw(local), scale, m['dark'])
        obj.rotation_euler.z = yaw
    for x in (-.11, .11):
        part('Unidentified legs', (x, 0, .45), (.075, .09, .45))
    part('Unidentified back', (0, 0, 1.18), (.21, .14, .45))
    part('Unidentified head | back only', (0, -.01, 1.72), (.105, .11, .14))
    for x in (-.25, .25):
        part('Unidentified arm', (x, .02, 1.12), (.06, .07, .36))
    cloth = k.box('Red cloth across rear shoulder', pw(L.CLOTH_LOCAL), (.40, .06, .22), m['red'], .03, yaw=yaw)
    cloth.rotation_euler.x = .08
    mark = k.empty('MARK | Person — stands by the lamp (back oblique to the river)', pw((0, 0, 0)), 'SINGLE_ARROW', .7)
    mark.rotation_euler.z = yaw
