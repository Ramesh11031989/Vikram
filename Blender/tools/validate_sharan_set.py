"""Check SET_Sharan.blend against the story: writes Blender/Sets/SET_Sharan_Validation.json.

  blender --background --python-exit-code 1 Blender/Sets/SET_Sharan.blend --python Blender/tools/validate_sharan_set.py
"""

import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sharan_layout as L

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'Blender/Sets/SET_Sharan_Validation.json'
scene = bpy.context.scene
checks = []
LOW_PROPS = ('Mat', 'Prop', 'Grass', 'SEAT', 'MARK', 'Rock', 'Board')


def record(name, passed, **detail):
    checks.append(dict(name=name, passed=bool(passed), detail=detail))


def blocked(origin, target, ignore=()):
    """Name of the first mesh between origin and target that is not in `ignore`, else None."""
    graph = bpy.context.evaluated_depsgraph_get()
    start, goal = Vector(origin), Vector(target)
    direction = (goal - start).normalized()
    distance = (goal - start).length
    while distance > .03:
        hit, location, _, _, obj, _ = scene.ray_cast(graph, start, direction, distance=distance - .02)
        if not hit:
            return None
        if not any(word in obj.name for word in ignore):
            return obj.name
        step = (location - start).length + .005
        start, distance = start + direction * step, distance - step
    return None


def surface_z(x, y, words):
    graph = bpy.context.evaluated_depsgraph_get()
    hit, location, _, _, obj, _ = scene.ray_cast(graph, Vector((x, y, 40.0)), Vector((0, 0, -1)), distance=80)
    return (location.z, obj.name) if hit and any(w in obj.name for w in words) else (None, obj.name if hit else None)


seats = L.seats()
gopal = seats[L.GOPAL_SEAT - 1]
record('Fourteen numbered seats exist as empties',
       len(seats) == 14 and sum(1 for o in bpy.data.objects if o.name.startswith('SEAT ')) == 14, seats=len(seats))
record('Gopal sits in the third place', gopal['n'] == 3 and any(o.name.startswith('SEAT 03 | Gopal') for o in bpy.data.objects))

eye = Vector((gopal['x'], gopal['y'], gopal['z'] + L.SEATED_EYE))
heard = []
for s in seats:
    if s['n'] > L.GOPAL_SEAT:
        d = math.hypot(s['x'] - gopal['x'], s['y'] - gopal['y'])
        heard.append((s['n'], round(d, 2), blocked(eye, (s['x'], s['y'], s['z'] + L.SEATED_EYE), LOW_PROPS)))
record(f'Every later seat (4-14) is within {L.HEARING_M} m of Gopal with a clear line of sight',
       all(d <= L.HEARING_M and sight is None for _, d, sight in heard), seats=heard)
record('At least 8 people sit after Gopal and can hear him', len(heard) >= 8, later=len(heard))

zs = [s['z'] for s in seats]
record('Seating terrace is level (within 0.25 m)', max(zs) - min(zs) < .25, spread=round(max(zs) - min(zs), 3))
record('Terrace is above the cremation ground and well below the hut platform',
       min(zs) > .5 and max(zs) < L.PLATFORM_Z - 2.0, terrace=[round(min(zs), 2), round(max(zs), 2)])
record('Every seat clears the footpath by at least 1.5 m', all(abs(s['x'] - L.path_x(s['y'])) > 1.5 for s in seats))
mausi = L.mausi()
record('Mausi sits beside Gopal (within 1 m)', math.hypot(mausi['x'] - gopal['x'], mausi['y'] - gopal['y']) < 1.0)
board = L.board_marks()['betal']
record('Betal and the sailors sit at the list board, inside the ring of seats',
       math.hypot(board[0] - L.SEAT_CENTRE[0], board[1] - L.SEAT_CENTRE[1]) < 1.5
       and min(math.hypot(s['x'] - L.SEAT_CENTRE[0], s['y'] - L.SEAT_CENTRE[1]) for s in seats) > 1.5)

grade = L.max_path_grade_deg()
record(f'Footpath never steeper than {L.MAX_GRADE_DEG} degrees for a man carrying a person',
       grade <= L.MAX_GRADE_DEG, max_grade=round(grade, 2))
record('Footpath is wide enough for Vikram with Betal (>= 1.2 m)', L.path_width() >= 1.2, width=L.path_width())
record('Path starts in the cremation-ground gap and reaches the hut veranda',
       abs(L.path_x(L.WALL_Y) - L.wall_gap_x()) < .01 and abs(L.path_x(L.PATH_Y[1]) - L.HUT['cx']) < .1
       and abs(L.PATH_Y[1] - L.veranda_front_y()) < 1.5)
sx, sy = L.path_x(L.WALL_Y), L.WALL_Y
wall_hit = blocked((sx, sy - 1.5, 1.0), (sx, sy + 1.5, 1.0))
record('The wall gap lets the walker through', wall_hit is None, hit=wall_hit)
z0, n0 = surface_z(L.path_x(20.0), 20.0, ('Path', 'Terrain', 'step', 'stone'))
record('Path surface follows the ground', z0 is not None and abs(z0 - L.ground_z(L.path_x(20.0), 20.0)) < .12, z=z0, hit=n0)

vm = L.veranda_mark()
roof_gap = blocked((vm[0], vm[1], vm[2] + .05), (vm[0], vm[1], vm[2] + L.VIKRAM_HEIGHT + .2))
record('Veranda is open overhead: Vikram (1.84 m) stands upright carrying Betal', roof_gap is None, hit=roof_gap)
record('Hut door is high enough (>= 1.7 m) and wide enough (>= 0.9 m)', L.HUT['door_h'] >= 1.7 and L.HUT['door_w'] >= .9)
door = L.door_centre()
door_view = blocked((door[0], door[1] - 2.5, door[2] + 1.0), (door[0], door[1] + .6, door[2] + 1.0), ('charpai',))
record('Door opening is clear from the veranda', door_view is None, hit=door_view)
record('Hut roof is above the door and overhangs the front wall',
       L.eave_z() > L.hut_floor_z() + L.HUT['door_h'] and L.ROOF_OVERHANG[0] > .3)
vz, vname = surface_z(vm[0], vm[1], ('plinth', 'Hut'))
record('Veranda floor is the hut plinth', vz is not None and abs(vz - L.hut_floor_z()) < .03, z=vz, hit=vname)
record('Hut platform is more than 3 m above the seating terrace', L.PLATFORM_Z - max(zs) > 3.0, rise=round(L.PLATFORM_Z - max(zs), 2))
cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
record('Six cameras and an active camera', len(cams) == 6 and scene.camera is not None, cameras=sorted(c.name for c in cams))

report = dict(blend='Blender/Sets/SET_Sharan.blend', all_passed=all(c['passed'] for c in checks), checks=checks)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('SHARAN_VALIDATION', report['all_passed'])
for check in checks:
    print(' ', 'PASS' if check['passed'] else 'FAIL', check['name'], check['detail'])
sys.exit(0 if report['all_passed'] else 1)
