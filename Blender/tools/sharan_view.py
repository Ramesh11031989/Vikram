"""Lights and cameras for SET_Sharan."""

import math

import bpy

import ghat_kit as k
import sharan_layout as L
from smashan_world import collection


def lights_and_cameras(scene):
    collection('Sharan | Lights and cameras')
    moon_data = bpy.data.lights.new('Moon', 'SUN')
    moon_data.energy, moon_data.color = 1.6, (.65, .75, 1.0)
    moon = bpy.data.objects.new('Moon', moon_data)
    moon.rotation_euler = (math.radians(55), 0, math.radians(-40))
    k._current.objects.link(moon)
    F, front = L.hut_floor_z(), L.hut_front_y()
    for name, loc, energy in (('Lantern glow', (L.HUT['cx'] + .85, front - .4, F + 1.64), 60),
                              ('Dhuni glow', (L.HUT['cx'] - 2.6, L.veranda_front_y() - .6, L.PLATFORM_Z + .4), 40)):
        data = bpy.data.lights.new(name, 'POINT')
        data.energy, data.color, data.shadow_soft_size = energy, (1.0, .6, .3), .15
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        k._current.objects.link(obj)

    def cam(name, loc, target, lens, active=False):
        data = bpy.data.cameras.new(name)
        data.lens, data.clip_end = lens, 400
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        k._current.objects.link(obj)
        k.aim(obj, target)
        if active:
            scene.camera = obj
        return obj

    g = L.gopal()
    px = L.path_x(30.0)
    cam('CAM | Slope from the foot', (3.0, -5.5, 2.0), (-2.0, 26.0, 3.6), 24, True)
    cam("CAM | Seating and Gopal's place", (L.path_x(9.0) - .5, 7.0, L.ground_z(L.path_x(9.0), 7.0) + 1.7),
        (g['x'], g['y'], g['z'] + .7), 30)
    cam('CAM | Path up to the hut', (px + .3, 27.0, L.ground_z(px, 27.0) + 1.5), (L.HUT['cx'], 42.0, F + 1.4), 30)
    cam('CAM | Hut exterior', (L.HUT['cx'] + 4.8, L.veranda_front_y() - 2.6, F + 1.7), (L.HUT['cx'], front, F + 1.1), 28)
    cam('CAM | Door close', (L.HUT['cx'] - 1.2, L.veranda_front_y() + .2, F + 1.5), (L.HUT['cx'], front, F + 1.0), 40)
    top = cam('CAM | Top map (sharan)', (0, 22, 75), (0, 22, 0), 35)
    top.rotation_euler = (0, 0, 0)
