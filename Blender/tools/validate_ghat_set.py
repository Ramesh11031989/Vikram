"""Check SET_Ghat.blend against the testimony: writes Blender/Sets/SET_Ghat_Validation.json.

  blender --background --python-exit-code 1 Blender/Sets/SET_Ghat.blend --python Blender/tools/validate_ghat_set.py
"""

import json
import math
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ghat_layout as L

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'Blender/Sets/SET_Ghat_Validation.json'
scene = bpy.context.scene
checks = []


def record(name, passed, **detail):
    checks.append(dict(name=name, passed=bool(passed), detail=detail))


def visible(origin, target, ignore=()):
    """True when no mesh other than the ones in `ignore` lies between origin and target."""
    graph = bpy.context.evaluated_depsgraph_get()
    direction = Vector(target) - Vector(origin)
    distance = direction.length
    start = Vector(origin)
    while True:
        hit, location, _, _, obj, _ = scene.ray_cast(graph, start, direction.normalized(), distance=distance - .02)
        if not hit:
            return True
        if not any(word in obj.name for word in ignore):
            return False
        step = (location - start).length + .005
        start, distance = start + direction.normalized() * step, distance - step


def in_frame(cam, point):
    p = world_to_camera_view(scene, cam, Vector(point))
    return 0 <= p.x <= 1 and 0 <= p.y <= 1 and p.z > 0, [round(p.x, 3), round(p.y, 3)]


def go(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()


def named(prefix):
    return next(o for o in bpy.data.objects if o.name.startswith(prefix))


eye = named('CAM | Boat POV — Gopal seated eye')
lamp = Vector(L.LAMP)
cloth = Vector(L.person_world(L.CLOTH_LOCAL))
gate_low = [Vector((x, L.GATE_Y, z)) for x in (-21.5, -21.0, -20.5) for z in (.2, .6, 1.0)]
spot = named('Lamp spot')
axis = spot.matrix_world.to_quaternion() @ Vector((0, 0, -1))

go(1)
origin = eye.matrix_world.translation
ok_lamp, pos_lamp = in_frame(eye, lamp)
ok_cloth, pos_cloth = in_frame(eye, cloth)
record('Frame 1: lamp flame is in the boat camera frame', ok_lamp, position=pos_lamp)
record('Frame 1: red cloth is in frame and the boat sees it (nothing blocks it)',
       ok_cloth and visible(origin, cloth, ('Red cloth', 'Unidentified', 'Lamp')), position=pos_cloth)
back = Vector((math.cos(math.radians(L.PERSON_FACING_DEG)), math.sin(math.radians(L.PERSON_FACING_DEG)), 0))
to_boat = Vector((origin.x - L.PERSON[0], origin.y - L.PERSON[1], 0)).normalized()
oblique = math.degrees(math.acos(max(-1, min(1, -back.dot(to_boat)))))
record('Person shows an oblique back to the boat (neither flat back nor profile)', 20 < oblique < 75,
       angle_between_back_and_boat_degrees=round(oblique, 1))

half_cone = L.LAMP_SPOT_DEG / 2
gate_angles = [math.degrees(axis.angle((p - spot.location))) for p in gate_low]
record('Lamp spot cone does not reach the gate below the lamp (stays dark)', min(gate_angles) > half_cone,
       half_cone_degrees=half_cone, nearest_gate_sample_degrees=round(min(gate_angles), 1))
cloth_angle = math.degrees(axis.angle(cloth - spot.location))
record('Lamp spot cone covers the red cloth', cloth_angle < half_cone, degrees_off_axis=round(cloth_angle, 1))

gate_z = {}
for frame in (1, 60, 120, 149, 240):
    go(frame)
    gate_z[frame] = round(named('Gate | grille root').location.z, 3)
record('Gate stays down through frame 149 and rises after the testimony',
       all(gate_z[f] == 0 for f in (1, 60, 120, 149)) and gate_z[240] > 2, grille_lift_by_frame=gate_z)

for frame, expected in ((1, True), (L.YAW_TURN_FRAMES[1] + 4, False), (120, False)):
    go(frame)
    flag_lamp, p_lamp = in_frame(eye, lamp)
    flag_cloth, p_cloth = in_frame(eye, cloth)
    seen = flag_lamp or flag_cloth
    record(f'Frame {frame}: chowki lamp and person {"in" if expected else "out of"} the boat camera frame',
           seen == expected, lamp=p_lamp, cloth=p_cloth)

go(1)
forward0 = (eye.matrix_world.to_quaternion() @ Vector((0, 0, -1)))
go(120)
forward1 = (eye.matrix_world.to_quaternion() @ Vector((0, 0, -1)))
to_chowki = (Vector((-17.0, 1.0, 1.0)) - eye.matrix_world.translation).normalized()
record('After the turn the boat looks away from the chowki', math.degrees(forward1.angle(to_chowki)) > 60,
       turn_degrees=round(math.degrees(forward0.angle(forward1)), 1),
       angle_to_chowki_degrees=round(math.degrees(forward1.angle(to_chowki)), 1))

record('Dry steps at night water level', len(L.dry_treads()) == 3, dry_treads=L.dry_treads())

report = dict(blend='Blender/Sets/SET_Ghat.blend', all_passed=all(c['passed'] for c in checks), checks=checks)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('GHAT_VALIDATION', report['all_passed'])
for check in checks:
    print(' ', 'PASS' if check['passed'] else 'FAIL', check['name'], check['detail'])
sys.exit(0 if report['all_passed'] else 1)
