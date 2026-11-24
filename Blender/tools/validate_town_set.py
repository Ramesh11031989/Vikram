"""Check SET_Town.blend against the story: writes Blender/Sets/SET_Town_Validation.json.

  blender --background --python-exit-code 1 Blender/Sets/SET_Town.blend --python Blender/tools/validate_town_set.py
"""

import json
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ghat_layout as G
import town_layout as T

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'Blender/Sets/SET_Town_Validation.json'
scene = bpy.context.scene
graph = bpy.context.evaluated_depsgraph_get()
checks = []


def record(name, passed, **detail):
    checks.append(dict(name=name, passed=bool(passed), detail=detail))


def first_hit(origin, target, ignore=()):
    """Name of the first mesh between origin and target that is not in `ignore`, else None."""
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


def named(prefix):
    return next(o for o in bpy.data.objects if o.name.startswith(prefix))


def drop(x, y):
    """First surface under (x, y) looking straight down from 30 m: (z, object name) or (None, None)."""
    hit, loc, _, _, obj, _ = scene.ray_cast(graph, Vector((x, y, 30)), Vector((0, 0, -1)), distance=40)
    return (round(loc.z, 3), obj.name) if hit else (None, None)


eye = T.HALWAI_EYE

# 1. The Halwai's roof sees the ghat (quay edge, mooring posts).
ghat_blockers = {str(tuple(round(c, 2) for c in p)): first_hit(eye, p) for p in T.GHAT_SAMPLES}
record('Halwai roof eye sees the ghat (quay edge and mooring posts) with nothing in between',
       all(v is None for v in ghat_blockers.values()), blockers=ghat_blockers)

# 2. The grain-market shed hides the gate from the same eye.
gate_blockers = {str(tuple(round(c, 2) for c in p)): first_hit(eye, p) for p in T.GATE_SAMPLES}
record('Every gate sample is hidden from the Halwai roof eye', all(v is not None for v in gate_blockers.values()),
       samples=len(gate_blockers), blockers=sorted({str(v) for v in gate_blockers.values()}))
record('The thing hiding the gate is the market shed, not a house',
       all(v and v.startswith('Mandi') for v in gate_blockers.values()))
without = {k: first_hit(eye, p, ('Mandi',)) for k, p in zip(gate_blockers, T.GATE_SAMPLES)}
record('Without the market shed most of the gate would be visible (the shed is what covers it)',
       sum(v is None for v in without.values()) > len(without) // 2,
       visible_without_shed=sum(v is None for v in without.values()), samples=len(without))

# 3. Ridge anchor and the sight line crossing the shed.
ridge = named('MARK | Mandi roof ridge')
record('Market ridge is at the palace map anchor', tuple(round(c, 3) for c in ridge.location) == tuple(T.RIDGE),
       location=[round(c, 3) for c in ridge.location])
t = (eye[1] - T.RIDGE[1]) / (eye[1] - T.GATE[1])
line_x, line_z = eye[0] + (T.GATE[0] - eye[0]) * t, eye[2] + (2.0 - eye[2]) * t
record('Sight line to the gate crosses the shed inside its footprint and below the ridge',
       T.MANDI['roof_x'][0] < line_x < T.MANDI['roof_x'][1] and line_z < T.RIDGE[2],
       crossing_x=round(line_x, 2), sight_line_z=round(line_z, 2), ridge_z=T.RIDGE[2])

# 4. Roof levels and the stair.
record('Halwai roof is higher than the front roof, and the eye is 1.7 m above its floor',
       T.HALWAI_ROOF_Z > T.FRONT_ROOF_Z and abs(eye[2] - T.HALWAI_ROOF_Z - T.EYE_HEIGHT) < .05,
       halwai_roof_z=T.HALWAI_ROOF_Z, front_roof_z=T.FRONT_ROOF_Z)
land_z, land_name = drop(T.STAIR['x'][1] - .5, T.STAIR['landing_to'] - .5)
record('Roof stair landing is level with the Halwai roof floor', land_z is not None and abs(land_z - T.HALWAI_ROOF_Z) < .02,
       landing_z=land_z, object=land_name, roof_z=T.HALWAI_ROOF_Z)
gap_y = (T.STAIR['parapet_gap'][0] + T.STAIR['parapet_gap'][1]) / 2
walk = first_hit((T.STAIR['x'][1] - .5, gap_y, T.HALWAI_ROOF_Z + .4), (T.HALWAI['center'][0], gap_y, T.HALWAI_ROOF_Z + .4))
record('A person on the stair landing can walk onto the roof through the parapet gap', walk is None, blocked_by=walk)

# 5. Front roof (सामने की छत): the boy who shouted is seen from the Halwai roof, and the roof does not block the ghat.
boy = Vector(T.FRONT_BOY)
boy_block = first_hit(eye, boy, ('Roof drying',))
record('The boy on the front roof is in line of sight of the Halwai roof', boy_block is None, blocker=boy_block)
record('Front roof is well below the Halwai eye, so it does not hide the ghat', T.FRONT_ROOF_Z < eye[2] - 1.0,
       front_roof_z=T.FRONT_ROOF_Z, eye_z=eye[2])

# 6. Cattle place (पड़ोसन का मवेशी बाँधने का स्थान).
stance = Vector(T.WEST_STANCE)
props = ('Cow', 'Hay', 'Hitching', 'Fodder', 'Cattle yard')
seen = {str(p): first_hit(stance, p, props) for p in T.CATTLE_SAMPLES}
record('From the Halwai west parapet the cattle place is visible (only its own props in between)',
       all(v is None for v in seen.values()), blockers=seen)
cows = [o for o in bpy.data.objects if o.name.startswith('Cow') and o.name.endswith('body')]
record('Cattle place has a hitching rail and two tethered cows',
       any(o.name == 'Hitching rail' for o in bpy.data.objects) and len(cows) == 2
       and sum(o.name.endswith('tether rope') for o in bpy.data.objects) == 2, cows=len(cows))
neighbour, halwai, yard = T.footprint(T.NEIGHBOUR), T.footprint(T.HALWAI), T.footprints()['Cattle place']
record('Neighbour house closes the yard on the west and the Halwai house on the east',
       abs(neighbour[2] - yard[0]) < .01 and abs(halwai[0] - yard[2]) < .01,
       neighbour_east=neighbour[2], yard_west=yard[0], yard_east=yard[2], halwai_west=halwai[0])

# 7. Open refuge floor: flat, open to the sky, nothing on it.
cx, cy = T.REFUGE['center']
w, d = T.REFUGE['size']
samples = [drop(cx - w / 2 + w * (i + .5) / 7, cy - d / 2 + d * (j + .5) / 6) for i in range(7) for j in range(6)]
record('Refuge floor is flat within 1 cm (joint relief), open to the sky, with nothing on it (42 samples)',
       all(z is not None and abs(z - T.REFUGE['top']) <= .01 and (n or '').startswith(('Refuge', 'Flag joint')) for z, n in samples),
       heights=sorted({z for z, _ in samples}), objects=sorted({str(n) for _, n in samples}))

# 8. Layout: nothing overlaps, houses stay off the lanes.
fp = T.footprints()
names = list(fp)
clashes = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]
           if T.overlaps(fp[a], fp[b]) and {a, b} != {'Mandi platform', 'Mandi roof'}]
record('No houses, cattle place, stair, refuge or shed overlap on the ground', not clashes, overlaps=clashes)
house_names = [s['name'] for s in T.HOUSES]
bad = [n for n in house_names if T.overlaps(fp[n], T.LANES['A']) or T.overlaps(fp[n], T.LANES['B'])]
record('Houses stay off lanes A and B', not bad, houses_on_lane=bad)
bad = [n for n in house_names + ['Refuge floor', 'Mandi platform'] if not (T.GROUND_X[0] <= fp[n][0] and fp[n][2] <= T.GROUND_X[1]
       and G.BANK_Y <= fp[n][1] and fp[n][3] <= T.TOWN_Y[1])]
record('Everything stands on the combined ghat-quay and town ground', not bad, outside=bad)

# 9. Modular houses.
roots = [o for o in bpy.data.objects if o.name.endswith('| root') and o.name.startswith(('Module', 'Halwai', 'Front', 'Neighbour'))]
kinds = {o.name for o in bpy.data.objects if o.name.startswith('Wall module')}
record('9 modular houses plus the 3 story houses, built from solid, door and window wall modules',
       len(roots) == 12 and {'Wall module solid', 'Wall module door', 'Wall module window'} <= {n.split('.')[0] for n in kinds},
       houses=len(roots), wall_module_kinds=sorted({n.split('.')[0] for n in kinds}))
bays = all(abs((fp[s['name']][2] - fp[s['name']][0]) / T.BAY - round((fp[s['name']][2] - fp[s['name']][0]) / T.BAY)) < 1e-6
           and abs((fp[s['name']][3] - fp[s['name']][1]) / T.BAY - round((fp[s['name']][3] - fp[s['name']][1]) / T.BAY)) < 1e-6
           for s in T.HOUSES)
record('Every house is a whole number of 3 m bays, with flat, thatch and tile roofs in use',
       bays and {s['roof'] for s in T.HOUSES} == {'flat', 'thatch', 'tile'}, roofs=sorted({s['roof'] for s in T.HOUSES}))

# 10. Shared map with the ghat set.
gate = named('MARK | Gate')
record('Gate in this scene is at the ghat-set position', abs(gate.location.x - G.GATE_X) < .01 and abs(gate.location.y - G.GATE_Y) < .01,
       location=[round(c, 2) for c in gate.location])
cam = named('CAM | Halwai roof eye to the ghat (wide)')
p = world_to_camera_view(scene, cam, Vector(T.GATE))
q = world_to_camera_view(scene, cam, Vector((0, G.BANK_Y, 0)))
record('Wide Halwai camera frames both the gate and the ghat centre',
       all(0 <= v <= 1 for v in (p.x, p.y, q.x, q.y)) and p.z > 0 and q.z > 0,
       gate=[round(p.x, 3), round(p.y, 3)], ghat=[round(q.x, 3), round(q.y, 3)])

report = dict(blend='Blender/Sets/SET_Town.blend', all_passed=all(c['passed'] for c in checks), checks=checks)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('TOWN_VALIDATION', report['all_passed'])
for check in checks:
    print(' ', 'PASS' if check['passed'] else 'FAIL', check['name'], check['detail'])
sys.exit(0 if report['all_passed'] else 1)
