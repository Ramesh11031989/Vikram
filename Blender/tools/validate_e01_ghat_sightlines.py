"""Check the camera and lighting geometry in E01_Ghat_Sightlines.blend."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


WINDOW = 'CAM | Chamber window — ghat steps (fixed)'
ROOF = 'CAM | Halwai roof eye to the ghat (wide)'
BOAT = 'CAM | Boat POV — Gopal seated eye'
CUTS = {1: WINDOW, 49: WINDOW, 97: ROOF, 145: BOAT, 238: BOAT}


def coords(vector, precision=3):
    return [round(value, precision) for value in vector]


def render_objects(layer):
    if layer.exclude or layer.collection.hide_render:
        return set()
    names = {obj.name for obj in layer.collection.objects if not obj.hide_render}
    for child in layer.children:
        names.update(render_objects(child))
    return names


class Probe:
    def __init__(self):
        self.scene = bpy.context.scene
        self.checks = []

    def frame(self, frame):
        self.scene.frame_set(frame)
        bpy.context.view_layer.update()
        self.graph = bpy.context.evaluated_depsgraph_get()
        self.render_objects = render_objects(bpy.context.view_layer.layer_collection)

    def find(self, prefix):
        exact = self.scene.objects.get(prefix)
        if exact is not None:
            return exact
        matches = [obj for obj in self.scene.objects if obj.name.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError(f'Expected one scene object matching {prefix!r}, found {[o.name for o in matches]}')
        return matches[0]

    def evaluated(self, obj):
        return obj.evaluated_get(self.graph)

    def position(self, obj):
        return self.evaluated(obj).matrix_world.translation.copy()

    def direction(self, obj, local_axis):
        return (self.evaluated(obj).matrix_world.to_quaternion() @ Vector(local_axis)).normalized()

    def bounds(self, obj):
        evaluated = self.evaluated(obj)
        points = [evaluated.matrix_world @ Vector(point) for point in evaluated.bound_box]
        return tuple(Vector(values) for values in (map(min, zip(*points)), map(max, zip(*points))))

    def in_frame(self, camera, target):
        evaluated = self.evaluated(camera)
        point = world_to_camera_view(self.scene, evaluated, Vector(target))
        return (0 < point.x < 1 and 0 < point.y < 1 and evaluated.data.clip_start < point.z < evaluated.data.clip_end,
                coords(point[:2]))

    def hit(self, origin, target, overshoot=-.016, skip=()):
        origin, target = Vector(origin), Vector(target)
        direction = (target - origin).normalized()
        remaining = (target - origin).length + overshoot
        start = origin.copy()
        # Advance through render-hidden rig aids and deliberately bypassed obstructions.
        for _ in range(64):
            if remaining <= 0:
                return None, math.inf
            hit, location, _, _, obj, _ = self.scene.ray_cast(self.graph, start, direction, distance=remaining)
            if not hit:
                return None, math.inf
            if obj.name in self.render_objects and not obj.name.startswith(skip):
                return obj, (location - origin).length
            step = (location - start).length + .004
            start += direction * step
            remaining -= step
        raise RuntimeError(f'Ray crossed too many skipped surfaces between {coords(origin)} and {coords(target)}')

    def record(self, name, passed, **detail):
        self.checks.append({'name': name, 'passed': bool(passed), 'detail': detail})


def check_camera_cuts(probe):
    cameras = {obj.name for obj in probe.scene.objects if obj.type == 'CAMERA'}
    probe.record('The combined scene contains the three witness cameras',
                 cameras == {WINDOW, ROOF, BOAT}, cameras=sorted(cameras))
    bound = {(marker.frame, marker.camera.name) for marker in probe.scene.timeline_markers if marker.camera}
    missing = {(frame, camera) for frame, camera in CUTS.items()} - bound
    probe.record('Timeline review markers bind each witness camera', not missing,
                 missing=[{'frame': frame, 'camera': camera} for frame, camera in sorted(missing)])


def check_window_steps(probe):
    camera = probe.find(WINDOW)
    water = probe.find('River water surface')
    steps = [probe.find(f'Ghat step {index}') for index in range(1, 9)]
    view_poses = []
    for frame, expected in ((1, 5), (49, 3)):
        probe.frame(frame)
        origin = probe.position(camera)
        evaluated_camera = probe.evaluated(camera)
        view_poses.append((evaluated_camera.matrix_world.copy(), evaluated_camera.data.lens))
        low_water, high_water = probe.bounds(water)
        water_z = (low_water.z + high_water.z) / 2
        seen_steps = []
        step_samples = []
        for number, step in enumerate(steps, 1):
            low, high = probe.bounds(step)
            dry = high.z > water_z + .02
            in_frame = 0
            seen = 0
            for sample in range(17):
                width_fraction = .075 + .85 * sample / 16
                point = Vector((low.x + width_fraction * (high.x - low.x), (low.y + high.y) / 2, high.z + .004))
                if not probe.in_frame(camera, point)[0]:
                    continue
                in_frame += 1
                hit, distance = probe.hit(origin, point, overshoot=.06)
                seen += hit == step and abs(distance - (point - origin).length) < .06
            if dry and seen >= 3:
                seen_steps.append(number)
            step_samples.append({'step': number, 'tread_z': round(high.z, 3), 'dry': dry,
                                 'samples_in_frame': in_frame, 'samples_on_tread': seen})
        probe.record(f'Frame {frame}: palace window sees exactly {expected} dry ghat treads',
                     seen_steps == list(range(1, expected + 1)) and water.name in probe.render_objects,
                     water_z=round(water_z, 3), dry_treads_seen=seen_steps, per_tread=step_samples)

    (morning, morning_lens), (later, later_lens) = view_poses
    same_view = all(math.isclose(a, b, abs_tol=1e-5) for row_a, row_b in zip(morning, later)
                    for a, b in zip(row_a, row_b)) and math.isclose(morning_lens, later_lens, abs_tol=1e-5)
    probe.record('The palace window camera and lens stay fixed as the water rises', same_view,
                 position=coords(morning.translation), lens_mm=round(morning_lens, 3))


def gate_targets(probe):
    mark = probe.find('MARK | Gate — lifting gate position (फाटक)')
    anchor = probe.position(mark)
    # Samples span the grille opening to the gate beam, just ahead of the gate on the town side.
    return anchor, [anchor + Vector((dx, .45, z)) for dx in (-.8, 0, .8) for z in (.4, 2., 4., 5.6)]


def check_roof_view(probe):
    probe.frame(97)
    camera = probe.find(ROOF)
    origin = probe.position(camera)
    gate_anchor, gate = gate_targets(probe)
    # These witness points cover the coping, mooring post and east cheek wall in the built ghat map.
    ghat = [Vector((10, -1, .84)), Vector((16, -1, .84)), Vector((5, -1.05, .85)), Vector((6.2, -1.8, .6))]

    def examine(points, skipped=()):
        result = []
        for point in points:
            in_frame, image = probe.in_frame(camera, point)
            hit, _ = probe.hit(origin, point, skip=skipped)
            result.append({'world': coords(point), 'image': image, 'in_frame': in_frame,
                           'blocker': hit.name if hit is not None else None})
        return result

    ghat_samples = examine(ghat)
    probe.record('Frame 97: the Halwai roof camera has an unobstructed view of the ghat',
                 all(sample['in_frame'] and not sample['blocker'] for sample in ghat_samples), samples=ghat_samples)
    gate_samples = examine(gate)
    aim_contains_gate = probe.in_frame(camera, gate_anchor)[0]
    blockers = [sample['blocker'] or '' for sample in gate_samples]
    roof_blocks = all(sample['in_frame'] and blocker.startswith('Mandi') and 'roof' in blocker.lower()
                      for sample, blocker in zip(gate_samples, blockers))
    probe.record('Frame 97: the market roof blocks the gate from the same Halwai camera',
                 aim_contains_gate and roof_blocks, samples=gate_samples)
    uncovered = examine(gate, ('Mandi',))
    open_rays = sum(sample['blocker'] is None for sample in uncovered)
    probe.record('The market shed is the determining gate obstruction',
                 open_rays > len(gate) / 2, rays_clear_without_shed=open_rays, rays_tested=len(gate))


def cloth_meshes(probe):
    cloth = [obj for obj in probe.scene.objects if obj.type == 'MESH' and obj.name in probe.render_objects
             and ('Red cloth over shoulders' in obj.name or obj.name.startswith('Red cloth across rear shoulder'))]
    if not cloth:
        raise ValueError('No rendered red cloth mesh is present at the chowki')
    return cloth


def cloth_points(probe, cloth, witness):
    points = []
    for obj in cloth:
        evaluated = probe.evaluated(obj)
        mesh = evaluated.to_mesh()
        try:
            faces = sorted(mesh.polygons,
                           key=lambda face: (evaluated.matrix_world @ face.center - witness).length)
            points.extend((obj, evaluated.matrix_world @ face.center) for face in faces[:128])
        finally:
            evaluated.to_mesh_clear()
    return points


def check_boat_view(probe):
    probe.frame(145)
    camera = probe.find(BOAT)
    seat = probe.find('Boat seat (Gopal)')
    boat = probe.find('Boat | root (route + yaw)')
    flame = probe.find('Lamp flame')
    spotlight = probe.find('Lamp spot (lights the person, not the gate)')
    witness_mark = probe.find('MARK | Red cloth witness sample')
    figure_back = probe.find('MARK | Red cloth figure root')
    camera_point = probe.position(camera)
    lamp_point = probe.position(flame)
    seat_height = probe.bounds(seat)[1].z
    lamp_visible, lamp_uv = probe.in_frame(camera, lamp_point)
    lamp_hit, _ = probe.hit(camera_point, lamp_point, skip=('Lamp flame',))
    probe.record('Frame 145: Gopal views the lamp from seated eye height',
                 lamp_visible and lamp_hit is None and .65 < (camera_point.z - seat_height) < 1.05
                 and flame.name in probe.render_objects,
                 below_eye_m=round(camera_point.z - seat_height, 3), lamp_image=lamp_uv,
                 blocker=lamp_hit.name if lamp_hit is not None else None)

    witness = probe.position(witness_mark)
    cloth = cloth_meshes(probe)
    lamp_origin = probe.position(spotlight)
    lamp_axis = probe.direction(spotlight, (0, 0, -1))
    spot_data = probe.evaluated(spotlight).data
    half_cone = spot_data.spot_size / 2
    visible, lit = 0, 0
    shadows = Counter()
    for obj, point in cloth_points(probe, cloth, witness):
        if not probe.in_frame(camera, point)[0]:
            continue
        hit, distance = probe.hit(camera_point, point, overshoot=.012)
        if hit != obj or abs(distance - (point - camera_point).length) > .004:
            continue
        visible += 1
        if lamp_axis.angle(point - lamp_origin) >= half_cone:
            continue
        light_hit, light_distance = probe.hit(lamp_origin, point, overshoot=.012, skip=('Lamp flame', 'Clay lamp bowl'))
        if light_hit == obj and abs(light_distance - (point - lamp_origin).length) < .004:
            lit += 1
        elif light_hit is not None:
            shadows[light_hit.name] += 1
    probe.record('Frame 145: the red cloth itself is visible and lit by the lamp spot',
                 visible >= 3 and lit >= 3 and spot_data.energy > 0 and spotlight.name in probe.render_objects,
                 visible_samples=visible, directly_lit_samples=lit, cloth=[obj.name for obj in cloth],
                 lamp_energy=round(spot_data.energy, 3), shadow_blockers=dict(shadows))

    back = probe.direction(figure_back, (0, 1, 0))
    toward_camera = camera_point - probe.position(figure_back)
    angle = Vector((back.x, back.y)).angle(Vector((toward_camera.x, toward_camera.y)))
    probe.record('Frame 145: Gopal faces the figure’s oblique back', 20 < math.degrees(angle) < 75,
                 angle_deg=round(math.degrees(angle), 2))

    gate_anchor, _ = gate_targets(probe)
    gate = [gate_anchor + Vector((dx, -.18, z)) for dx in (-.5, 0, .5) for z in (.2, .6, 1.)]
    nearest_gate = min(lamp_axis.angle(point - lamp_origin) for point in gate)
    probe.record('Frame 145: the lamp’s direct cone excludes the lower gate', nearest_gate > half_cone,
                 nearest_gate_off_axis_deg=round(math.degrees(nearest_gate), 2),
                 cone_half_angle_deg=round(math.degrees(half_cone), 2))

    initial_direction = probe.direction(camera, (0, 0, -1))
    initial_boat_direction = probe.direction(boat, (0, 1, 0))
    probe.frame(238)
    final_direction = probe.direction(camera, (0, 0, -1))
    final_boat_direction = probe.direction(boat, (0, 1, 0))
    toward_lamp = probe.position(flame) - probe.position(camera)
    angle_after_turn = math.degrees(final_direction.angle(toward_lamp))
    heading_change = math.degrees(initial_direction.angle(final_direction))
    boat_heading_change = math.degrees(initial_boat_direction.angle(final_boat_direction))
    final_lamp_visible, final_lamp_uv = probe.in_frame(camera, probe.position(flame))
    final_cloth_visible, final_cloth_uv = probe.in_frame(camera, probe.position(witness_mark))
    probe.record('Frame 238: the boat has swung its view away from the chowki',
                 not final_lamp_visible and not final_cloth_visible and heading_change > 60 and angle_after_turn > 60
                 and boat_heading_change > 60,
                 camera_heading_change_deg=round(heading_change, 2), boat_heading_change_deg=round(boat_heading_change, 2),
                 chowki_off_axis_deg=round(angle_after_turn, 2),
                 lamp_image=final_lamp_uv, cloth_image=final_cloth_uv)

    grille = probe.find('Gate | grille root')
    heights = {}
    for frame in (145, 238, 293, 354):
        probe.frame(frame)
        heights[frame] = probe.position(grille).z
    height_change = heights[354] - heights[145]
    probe.record('The gate remains closed through the boat testimony and lifts later',
                 abs(heights[145] - gate_anchor.z) < .04
                 and all(abs(heights[frame] - heights[145]) < .02 for frame in (238, 293)) and height_change > 2,
                 grille_root_z={frame: round(value, 3) for frame, value in heights.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional output path for the JSON check report.')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    probe = Probe()
    original_frame = probe.scene.frame_current
    try:
        check_camera_cuts(probe)
        check_window_steps(probe)
        check_roof_view(probe)
        check_boat_view(probe)
    finally:
        probe.scene.frame_set(original_frame)

    passed = all(check['passed'] for check in probe.checks)
    report = {'blend': Path(bpy.data.filepath).name, 'scene': probe.scene.name,
              'all_passed': passed, 'checks': probe.checks}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for check in probe.checks:
        print(f"{'PASS' if check['passed'] else 'FAIL'} | {check['name']}", flush=True)
        if not check['passed']:
            print(json.dumps(check['detail'], ensure_ascii=False), flush=True)
    if not passed:
        raise RuntimeError('The combined scene failed one or more sightline checks')


if __name__ == '__main__':
    main()
