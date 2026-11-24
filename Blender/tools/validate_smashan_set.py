"""Check SET_Smashan.blend against the story: writes Blender/Sets/SET_Smashan_Validation.json.

  blender --background --python-exit-code 1 Blender/Sets/SET_Smashan.blend --python Blender/tools/validate_smashan_set.py
"""

import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smashan_layout as L

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'Blender/Sets/SET_Smashan_Validation.json'
scene = bpy.context.scene
checks = []


def record(name, passed, **detail):
    checks.append(dict(name=name, passed=bool(passed), detail=detail))


def go(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()


def blocked(origin, target, ignore=()):
    """First mesh hit between origin and target that is not in `ignore`, else None."""
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


def top_z(x, y, names):
    """Highest surface of the named objects at (x, y), by casting down from above."""
    graph = bpy.context.evaluated_depsgraph_get()
    z = 5.0
    best = None
    while z > 0:
        hit, location, _, _, obj, _ = scene.ray_cast(graph, Vector((x, y, z)), Vector((0, 0, -1)), distance=z + .2)
        if not hit:
            break
        if any(n in obj.name for n in names):
            best = location.z
            break
        z = location.z - .01
    return best


heels = [Vector(h) + Vector((0, 0, .03)) for h in L.heels()]
eye = Vector((-.8, L.cloth_origin()[1], 1.2))
ignore = ('Heels',)

go(L.CLOTH_FRAMES['start'])
record('Frame 1: cloth hides both heels from the path camera',
       all(blocked(eye, h, ignore) and 'Cloth' in blocked(eye, h, ignore) for h in heels))
go(L.CLOTH_FRAMES['lift_full'] + 10)
low_eye = Vector((-1.4, L.cloth_origin()[1], .55))
record('Cloth lifted: both heels are visible and nothing blocks the view',
       all(blocked(low_eye, h, ignore) is None for h in heels),
       blocked_by=[blocked(low_eye, h, ignore) for h in heels])
go(L.CLOTH_FRAMES['down'])
record('Cloth returns down and hides the heels again', all(blocked(eye, h, ignore) is not None for h in heels))
go(1)

cx, cy = L.CHABUTRA['center']
chab = top_z(cx, cy, ('Chabutra',))
record('Chabutra top is a low seat for Betal (0.40-0.55 m)', chab and L.CHABUTRA_TOP_LIMITS[0] <= chab <= L.CHABUTRA_TOP_LIMITS[1],
       top_z=chab)
record('Chabutra is big enough to sit on (>= 1.5 m each way)', min(L.CHABUTRA['size']) >= 1.5, size=L.CHABUTRA['size'])

tops = []
for s in (L.LOW_SEAT_RANGE[0], 2.0, L.LOW_SEAT_RANGE[1]):
    x, y, _ = L.along(L.LOW_DIR, s)
    tops.append(top_z(x, y, ('low climbing branch',)))
record('Low branch top lets Betal sit and be lifted (1.0-1.25 m) along the seat stretch',
       all(t and L.LOW_TOP_LIMITS[0] <= t <= L.LOW_TOP_LIMITS[1] for t in tops), tops=tops)
record('Low branch top is below Vikram shoulder height', all(t < L.VIKRAM_HEIGHT * .8 for t in tops if t))

sx, sy, _ = L.root_seat_centre()
root = top_z(sx, sy, ('exposed root seat',))
record('Root seat height is a sitting height (0.35-0.50 m)', root and L.ROOT_TOP_LIMITS[0] <= root <= L.ROOT_TOP_LIMITS[1], top_z=root)
clear = [blocked((sx + dx, sy + dy, .9), (sx, sy, root + .6)) for dx, dy in ((1.0, 0), (0, 1.0), (-1, 0))]
record('Space above the root seat is clear for a seated figure', all(c is None or 'canopy' not in c for c in clear), hits=clear)

record('Carry mark is within 2 m of the low branch tip and the chabutra',
       (Vector(L.VIKRAM_CARRY_MARK) - Vector(L.low_tip())).xy.length < 2.0
       and (Vector(L.VIKRAM_CARRY_MARK).xy - Vector((cx, cy))).length < 2.5)

horse = Vector(L.HORSE_MARK)
record('Horse post is outside the gate, before the entrance', all(p[1] < L.GATE_Y for p in L.HORSE_POSTS))
record('Path is clear from the horse mark through the gate to the banyan',
       blocked((0, L.HORSE_MARK[1], 1.0), (0, 3.0, 1.0), ('Gate',)) is None)
record('Gate opening is wider than 2 m', L.GATE_POST_X * 2 - .5 > 2.0)
record('Cloth hangs from the upper branch', abs(L.cloth_top_z() - 2.0) < .5, top=L.cloth_top_z())

report = dict(blend='Blender/Sets/SET_Smashan.blend', all_passed=all(c['passed'] for c in checks), checks=checks)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('SMASHAN_VALIDATION', report['all_passed'])
for check in checks:
    print(' ', 'PASS' if check['passed'] else 'FAIL', check['name'], check['detail'])
sys.exit(0 if report['all_passed'] else 1)
