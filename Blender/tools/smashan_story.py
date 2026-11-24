"""Banyan, hanging cloth with heels, chabutra, pyres, lights and cameras for SET_Smashan."""

import math
import random

import bpy

import ghat_kit as k
import smashan_layout as L
import smashan_props as P
from smashan_banyan import banyan_detail
from smashan_world import collection, limb, tube


def banyan(m):
    collection('Smashan | Banyan')
    tx, ty = L.TRUNK
    trunk_pts = [(tx, ty, -.1), (tx + .05, ty - .05, .6), (tx, ty, 1.4), (tx - .1, ty + .1, 2.4), (tx - .2, ty + .15, 3.4)]
    tube('Banyan | main trunk', trunk_pts, [.62, .5, .42, .36, .3], m['bark'], sides=16)
    for i in range(7):  # buttress flares at the foot
        a = math.tau * i / 7 + .3
        k.rod(f'Banyan | foot flare {i + 1}', (tx + math.cos(a) * .5, ty + math.sin(a) * .5, .45),
              (tx + math.cos(a) * 1.2, ty + math.sin(a) * 1.2, .03), .13, m['root'], vertices=8)
    limb('Banyan | low climbing branch', L.LOW_DIR, L.LOW_PROFILE, m['bark'])
    limb('Banyan | upper branch (cloth)', L.UP_DIR, L.UP_PROFILE, m['bark'])
    limb('Banyan | exposed root seat', L.ROOT_DIR, L.ROOT_PROFILE, m['root'], steps=16, sway=.05)
    banyan_detail(m)
    k.empty('MARK | Banyan trunk', (tx, ty, 0), 'CIRCLE', 1.2)


def cloth_and_heels(m):
    collection('Smashan | Hanging cloth and heels')
    cx, cy = L.cloth_origin()
    top, hem = L.cloth_top_z(), L.CLOTH_HEM_Z
    rows, cols = 14, 6
    verts, faces = [], []
    for r in range(rows + 1):
        z = top - (top - hem) * r / rows
        for c in range(cols + 1):
            y = -L.CLOTH_WIDTH / 2 + L.CLOTH_WIDTH * c / cols
            verts.append((cx + .03 * math.sin(c * 1.8 + r * .3), cy + y, z))
    for r in range(rows):
        for c in range(cols):
            a = r * (cols + 1) + c
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    cloth = k.mesh_object('Cloth | white hanging cloth', verts, faces, m['cloth'], smooth=True)
    solid = cloth.modifiers.new('Cloth thickness', 'SOLIDIFY')
    solid.thickness = .006
    cloth.shape_key_add(name='Basis')
    lifted = cloth.shape_key_add(name='Hem lifted')
    height = top - hem
    for index, v in enumerate(lifted.data):
        u = (index // (cols + 1)) / rows  # 0 at the top, 1 at the hem
        weight = max(0.0, (u - .25) / .75) ** 1.4
        c = index % (cols + 1)
        v.co.z += weight * (height * .30 + .22)
        v.co.x -= weight * .42
        v.co.y += (c - cols / 2) * .06 * weight
    f = L.CLOTH_FRAMES
    for frame, value in ((f['start'], 0), (f['lift_begin'], 0), (f['lift_full'], 1), (f['hold_until'], 1), (f['down'], 0)):
        lifted.value = value
        lifted.keyframe_insert('value', frame=frame)
    k.rod('Cloth | tie knot', (cx, cy - .2, top + .02), (cx, cy + .2, top + .02), .035, m['cloth'], vertices=8)
    for side, (hx, hy, hz) in zip(('left', 'right'), L.heels()):
        k.sphere(f'Heels | {side} heel', (hx, hy, hz + .04), (.045, .04, .04), m['skin'])
        k.rod(f'Heels | {side} ankle and shin', (hx, hy, hz + .06), (hx + .03, hy, 1.1), .035, m['skin'], vertices=8)
        k.box(f'Heels | {side} foot (toes hidden)', (hx + .1, hy, hz), (.2, .08, .035), m['skin'], bevel=.01)
    k.empty('MARK | Cloth lifts here', (cx, cy, top), 'PLAIN_AXES', .4)
    k.empty('MARK | Heels', (cx + L.HEEL_GAP, cy, L.HEEL_Z), 'SPHERE', .12)



def chabutra(m):
    collection('Smashan | Chabutra')
    (cx, cy), (sx, sy) = L.CHABUTRA['center'], L.CHABUTRA['size']
    h = L.CHABUTRA['height']
    P.chabutra_detail(m)
    k.empty('MARK | Vikram carries Betal here', L.VIKRAM_CARRY_MARK, 'ARROWS', .5)
    k.empty('MARK | Betal seat on chabutra', (cx, cy, h), 'PLAIN_AXES', .3)
    k.empty('MARK | Betal seat on root (last scene)', L.root_seat_centre(), 'PLAIN_AXES', .3)
    k.empty('MARK | Betal seat on low branch', (*L.along(L.LOW_DIR, 2.0)[:2], L.low_top(2.0)), 'PLAIN_AXES', .3)


def pyres(m):
    collection('Smashan | Cremation ground')
    for i, (x, y, logs) in enumerate(L.PYRES, start=1):
        P.pyre(x, y, logs, i, m)
    for i, (x, y) in enumerate(L.MEMORIALS, start=1):
        P.memorial(x, y, i, m)


def lights_and_cameras(scene):
    collection('Smashan | Lights and cameras')
    data = bpy.data.lights.new('Moon', 'SUN')
    data.energy, data.color = 1.6, (.65, .75, 1.0)
    moon = bpy.data.objects.new('Moon', data)
    moon.rotation_euler = (math.radians(55), 0, math.radians(-40))
    k._current.objects.link(moon)
    cx, cy = L.cloth_origin()
    seat = L.root_seat_centre()

    def cam(name, loc, target, lens, active=False):
        data = bpy.data.cameras.new(name)
        data.lens = lens
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        k._current.objects.link(obj)
        k.aim(obj, target)
        if active:
            scene.camera = obj
        return obj

    cam('CAM | Cloth and heels from the path', (-.8, cy, 1.2), (cx, cy, .9), 35, True)
    cam('CAM | Heels close', (cx - 1.4, cy - .2, .35), (cx + .2, cy, .12), 50)
    cam('CAM | Entrance and horse', (-2.0, -12.0, 1.6), (0, -5, 1.2), 28)
    cam('CAM | Banyan, branch and chabutra', (-3.5, -3.0, 1.7), (3.2, 3.2, 1.1), 24)
    cam('CAM | Root seat', (seat[0] + 2.0, seat[1] + 1.2, .9), (seat[0], seat[1], .4), 35)
    top = cam('CAM | Top map (smashan)', (0, 4, 38), (0, 4, 0), 35)
    top.rotation_euler = (0, 0, 0)
