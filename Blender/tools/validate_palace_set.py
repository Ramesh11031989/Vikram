"""Check the palace set against the story's sight-line requirements.

    python Blender/tools/validate_palace_set.py
    blender --background Blender/Sets/SET_Palace.blend --python Blender/tools/validate_palace_set.py

Checks, by ray casting the evaluated scene:
  1. The fixed ghat-window camera sees exactly five dry ghat treads in the
     morning frame and three in the evening frame.
  2. The next witness in the waiting hall cannot see the interrogation floor.
  3. The chalk-map floor in the interrogation room is empty and flat.
  4. The darbar story camera sees the public entrance, the daughter's path and
     the mark for Nandu's hands with nothing of the set in the way.
  5. From the reading spot, the guard at the chamber door is in clear view.

Writes Blender/Sets/SET_Palace_Validation.json and exits 1 if a check fails.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import set_world_map as world  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / 'Blender' / 'Sets' / 'SET_Palace.blend'
MANIFEST = ROOT / 'Blender' / 'Sets' / 'SET_Palace_Manifest.json'
REPORT = ROOT / 'Blender' / 'Sets' / 'SET_Palace_Validation.json'


@dataclass
class Check:
    name: str
    passed: bool
    detail: dict[str, object] = field(default_factory=dict)


class Probe:
    def __init__(self) -> None:
        self.scene = bpy.context.scene
        self.refresh()

    def refresh(self) -> None:
        bpy.context.view_layer.update()
        self.depsgraph = bpy.context.evaluated_depsgraph_get()

    def first_hit(self, origin: Vector, target: Vector) -> tuple[bool, float, str]:
        direction = target - origin
        distance = direction.length
        hit, location, _normal, _index, obj, _matrix = self.scene.ray_cast(
            self.depsgraph, origin, direction.normalized(), distance=distance + 0.5)
        if not hit:
            return False, math.inf, ''
        return True, (location - origin).length, obj.name

    def clear(self, origin: Vector, target: Vector, tolerance: float = 0.08) -> bool:
        hit, dist, _ = self.first_hit(origin, target)
        return not hit or dist >= (target - origin).length - tolerance

    def in_frame(self, camera: bpy.types.Object, point: Vector) -> bool:
        co = world_to_camera_view(self.scene, camera, point)
        return 0.0 < co.x < 1.0 and 0.0 < co.y < 1.0 and co.z > 0.0


def ghat_steps(probe: Probe, camera: bpy.types.Object, frame: int, expected: int) -> Check:
    probe.scene.frame_set(frame)
    probe.refresh()
    water = bpy.data.objects['River | water surface (keyed level)']
    water_z = water.matrix_world.translation.z
    origin = camera.matrix_world.translation.copy()
    per_step: list[dict[str, object]] = []
    dry_visible: list[int] = []
    for step in range(1, 9):
        top = world.step_top_z(step)
        y = world.step_front_y(step) + 0.18
        dry = top > water_z + 0.02
        seen = 0
        framed = 0
        samples = 17
        for i in range(samples):
            x = world.GHAT_CENTER_X - world.GHAT_HALF_WIDTH + 1.0 + i * (2 * world.GHAT_HALF_WIDTH - 2.0) / (samples - 1)
            point = Vector((x, y, top + 0.004))
            if not probe.in_frame(camera, point):
                continue
            framed += 1
            hit, dist, name = probe.first_hit(origin, point)
            if hit and name.startswith('Ghat | 14 steps') and abs(dist - (point - origin).length) < 0.15:
                seen += 1
        visible = dry and seen >= 3
        if visible:
            dry_visible.append(step)
        per_step.append({'step': step, 'tread_z': round(top, 2), 'dry': dry, 'samples_in_frame': framed,
                         'samples_seen': seen, 'counted': visible})
    contiguous = dry_visible == list(range(1, len(dry_visible) + 1))
    passed = contiguous and len(dry_visible) == expected
    return Check(f'{camera.name} — frame {frame}: {expected} dry steps', passed,
                 {'water_z': round(water_z, 3), 'counted_steps': dry_visible, 'per_step': per_step})


def witness_isolated(probe: Probe, marks: dict[str, dict[str, object]]) -> Check:
    probe.scene.frame_set(1)
    probe.refresh()
    chalk = Vector(marks['chalk']['world'])
    targets = []
    for dx in (-1.6, 0.0, 1.6):
        for dy in (-1.2, 0.0, 1.2):
            local = world.world_to_palace(tuple(chalk))
            targets.append(Vector(world.palace_to_world((local[0] + dx, local[1] + dy, local[2] + 1.0))))
    eyes = []
    seat = Vector(marks['next_witness']['world'])
    eyes.append(seat + Vector((0, 0, 0.75)))
    for lx in (-17.6, -15.0, -12.5, -10.8):
        for ly in (-22.4, -20.0, -17.8, -15.0):
            eyes.append(Vector(world.palace_to_world((lx, ly, 0.6 + 1.6))))
    open_lines = 0
    total = 0
    for eye in eyes:
        for target in targets:
            total += 1
            if probe.clear(eye, target):
                open_lines += 1
    return Check('Next witness cannot see the interrogation floor', open_lines == 0,
                 {'sight_lines_tested': total, 'sight_lines_open': open_lines})


def chalk_floor_empty(probe: Probe, marks: dict[str, dict[str, object]]) -> Check:
    probe.refresh()
    centre = world.world_to_palace(tuple(marks['chalk']['world']))
    half = (2.0, 1.6)
    bad: list[str] = []
    heights: list[float] = []
    for i in range(9):
        for j in range(7):
            lx = centre[0] - half[0] + i * 2 * half[0] / 8
            ly = centre[1] - half[1] + j * 2 * half[1] / 6
            top = Vector(world.palace_to_world((lx, ly, 3.2)))
            bottom = Vector(world.palace_to_world((lx, ly, 0.0)))
            hit, dist, name = probe.first_hit(top, bottom)
            if not hit or 'floor' not in name.lower():
                bad.append(name or 'nothing')
            else:
                heights.append(round(top.z - dist, 4))
    flat = bool(heights) and (max(heights) - min(heights)) < 0.002
    return Check('Chalk-map floor is empty and flat', not bad and flat,
                 {'samples': 63, 'obstructions': sorted(set(bad)), 'floor_height_range_m':
                  round(max(heights) - min(heights), 5) if heights else None, 'zone_m': [4.0, 3.2]})


def darbar_line(probe: Probe, cameras: dict[str, dict[str, object]], marks: dict[str, dict[str, object]]) -> Check:
    probe.scene.frame_set(1)
    probe.refresh()
    camera = bpy.data.objects[cameras['darbar_story']['name']]
    origin = camera.matrix_world.translation.copy()
    entrance = Vector(marks['daughter']['world']) + Vector((0, 0, 0.95))
    hands = Vector(marks['nandu_hands']['world'])
    path = bpy.data.objects[marks['daughter_path']['name']]
    points = [path.matrix_world @ Vector(p.co[:3]) for p in path.data.splines[0].points]
    samples: list[Vector] = []
    for a, b in zip(points, points[1:]):
        for t in range(6):
            p = a.lerp(b, t / 6)
            samples += [p + Vector((0, 0, 0.6)), p + Vector((0, 0, 0.95))]
    path_seen = sum(1 for p in samples if probe.in_frame(camera, p) and probe.clear(origin, p))
    result = {
        'entrance_in_frame': probe.in_frame(camera, entrance),
        'entrance_clear': probe.clear(origin, entrance),
        'hands_in_frame': probe.in_frame(camera, hands),
        'hands_clear': probe.clear(origin, hands),
        'entrance_to_hands_clear': probe.clear(entrance, hands),
        'path_samples_seen': f'{path_seen}/{len(samples)}',
    }
    passed = all(v for k, v in result.items() if isinstance(v, bool)) and path_seen >= 0.9 * len(samples)
    return Check("Darbar camera: daughter's entrance to Nandu's hands", passed, result)


def guard_door(probe: Probe, marks: dict[str, dict[str, object]]) -> Check:
    probe.refresh()
    reader = Vector(marks['reading']['world']) + Vector((0, 0, 0.8))
    guard = Vector(marks['guard_door']['world']) + Vector((0, 0, 1.6))
    return Check('Reading spot sees the guard at the chamber door', probe.clear(reader, guard),
                 {'distance_m': round((guard - reader).length, 2)})


def main() -> None:
    if Path(bpy.data.filepath or '').resolve() != BLEND.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    marks, cameras = data['story_marks'], data['cameras']
    probe = Probe()
    checks: list[Check] = []
    for key in ('window', 'window_tele'):
        camera = bpy.data.objects[cameras[key]['name']]
        checks.append(ghat_steps(probe, camera, 1, world.MORNING_VISIBLE_STEPS))
        checks.append(ghat_steps(probe, camera, 2, world.EVENING_VISIBLE_STEPS))
    checks.append(witness_isolated(probe, marks))
    checks.append(chalk_floor_empty(probe, marks))
    checks.append(darbar_line(probe, cameras, marks))
    checks.append(guard_door(probe, marks))
    probe.scene.frame_set(1)
    report = {'blend': str(BLEND.relative_to(ROOT)).replace('\\', '/'), 'all_passed': all(c.passed for c in checks),
              'checks': [asdict(c) for c in checks]}
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for c in checks:
        summary = {k: v for k, v in c.detail.items() if k != 'per_step'}
        print(f"{'PASS' if c.passed else 'FAIL'} | {c.name} | {summary}", flush=True)
    if not report['all_passed']:
        sys.exit(1)


if __name__ == '__main__':
    main()
