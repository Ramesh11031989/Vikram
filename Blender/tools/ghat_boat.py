"""Ghat set boat, boat route and cameras."""

import math

import bpy

import ghat_kit as k
import ghat_layout as L

BOAT_COLLECTION = 'Ghat | Boat & route (नाव का रास्ता)'


def hull(m):
    stations = [(-2.3, .02, .58), (-1.6, .38, .50), (-.6, .55, .50), (.6, .55, .50), (1.6, .38, .50), (2.3, .02, .58)]
    verts, faces = [], []
    for y, w, top in stations:
        verts += [(-w, y, top), (-w * .72, y, .05), (0, y, -.10), (w * .72, y, .05), (w, y, top)]
    for i in range(len(stations) - 1):
        for j in range(4):
            a = 5 * i + j
            faces.append((a, a + 1, a + 6, a + 5))
    last = 5 * (len(stations) - 1)
    faces += [(4, 3, 2, 1, 0), (last, last + 1, last + 2, last + 3, last + 4)]
    return k.mesh_object('Boat | hull', verts, faces, m['wood'], smooth=False)


def boat(m):
    k.use(k.collection(BOAT_COLLECTION))
    root = k.empty('Boat | root (route + yaw)', (0, 0, L.WATER_Z), 'PLAIN_AXES', .8)
    rock = k.empty('Boat | hull rock', (0, 0, 0), 'PLAIN_AXES', .5)
    rock.parent = root
    parts = [hull(m),
             k.box('Boat floor plank', (0, 0, .03), (.8, 3.4, .04), m['wood'], .01),
             k.box('Boat seat (Gopal)', (0, -.3, .32), (.9, .32, .05), m['wood'], .01),
             k.box('Boat thwart', (0, 1.0, .34), (.95, .26, .05), m['wood'], .01),
             k.rod('Oar shaft', (.45, -.1, .42), (1.55, .9, -.15), .028, m['wood']),
             k.box('Oar blade', (1.6, 1.0, -.16), (.16, .55, .04), m['wood'], .01)]
    for part in parts:
        part.parent = rock
    for frame in sorted(set(list(range(1, L.FRAME_END + 1, 6)) + [L.FRAME_END])):
        x, y = L.boat_xy(frame)
        root.location = (x, y, L.WATER_Z)
        root.rotation_euler.z = L.boat_yaw(frame)
        root.keyframe_insert('location', frame=frame)
        root.keyframe_insert('rotation_euler', index=2, frame=frame)
        rock.rotation_euler = (math.radians(1.2) * math.sin(frame * math.tau / 70.0),
                               math.radians(.7) * math.sin(frame * math.tau / 52.0 + 1), 0)
        rock.keyframe_insert('rotation_euler', frame=frame)
    curve = bpy.data.curves.new('Boat route', 'CURVE')
    curve.dimensions, curve.bevel_depth, curve.resolution_u = '3D', .05, 12
    spline = curve.splines.new('POLY')
    spline.points.add(len(L.BOAT_ROUTE) - 1)
    for point, (x, y) in zip(spline.points, L.BOAT_ROUTE):
        point.co = (x, y, L.WATER_Z + .03, 1)
    path = bpy.data.objects.new('Boat route (नाव का रास्ता)', curve)
    path.data.materials.append(m['route'])
    k._current.objects.link(path)
    for index, (x, y) in enumerate(L.BOAT_ROUTE):
        k.empty(f'MARK | Boat route point {index}', (x, y, L.WATER_Z), 'SPHERE', .25)
    return rock


def camera(name, lens, location, target=None, parent=None, rotation=None, ortho=None):
    data = bpy.data.cameras.new(name)
    data.lens, data.clip_end, data.sensor_width = lens, 400, 36
    if ortho:
        data.type, data.ortho_scale = 'ORTHO', ortho
    obj = bpy.data.objects.new(name, data)
    k._current.objects.link(obj)
    obj.location = location
    if parent:
        obj.parent, obj.rotation_euler = parent, rotation
    elif target:
        k.aim(obj, target)
    return obj


def cameras(scene, rock):
    k.use(k.collection('Ghat | Cameras'))
    pitch = (math.radians(90 + L.EYE_PITCH_DEG), 0, 0)
    boat_eye = camera('CAM | Boat POV — Gopal seated eye', 35, L.SEAT_EYE, parent=rock, rotation=pitch)
    camera('CAM | Boat POV — wide', 22, L.SEAT_EYE, parent=rock, rotation=pitch)
    camera('CAM | Gate and lamp from the river', 50, (-19.5, -9.0, -.2), target=(-19.8, 0, 1.4))
    camera('CAM | Quay west — gate and chowki', 28, (-8.0, 4.5, 1.7), target=(-19.0, .6, 1.4))
    camera('CAM | Steps from the river', 30, (4.0, -14.0, 1.2), target=(0, -3.0, -.8))
    camera('CAM | Top map (river bend, ghat, boat route)', 24, (-5, -2, 140), target=(-5, -2, 0), ortho=130)
    scene.camera = boat_eye
    for frame, name in ((1, 'Boat faces chowki lamp and red cloth'),
                        (L.YAW_TURN_FRAMES[0], 'Boat begins to yaw downstream'),
                        (L.YAW_TURN_FRAMES[1], 'Lamp has left the frame'),
                        (L.GATE_RAISE_FRAMES[0], 'After testimony: gate rises')):
        scene.timeline_markers.new(name, frame=frame)


def lights():
    k.use(k.collection('Ghat | Lights'))
    for name, location, target, color, energy in (('Quay faint moon bounce', (-6, 12, 14), (0, 0, 0), (.45, .58, .95), 6),
                                                  ('Water glint', (-10, -24, 10), (-10, -10, L.WATER_Z), (.35, .5, .8), 8)):
        data = bpy.data.lights.new(name, 'AREA')
        data.color, data.energy, data.shape, data.size = color, energy, 'DISK', 10
        obj = bpy.data.objects.new(name, data)
        k._current.objects.link(obj)
        obj.location = location
        k.aim(obj, target)
