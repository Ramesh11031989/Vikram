"""Export the staged interrogation and its 24 fps camera edit to Unity."""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_e01_unity_sightlines import UNITY_BASIS, add_calibration, color, vector


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Unity/Assets/Art/E01/SC04'
TIMELINE = ROOT / 'Production/E01/E01_SC04_Animatic_Timeline.json'
ASSET_TYPES = {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META', 'ARMATURE'}


def transform_data(obj):
    matrix = obj.matrix_world
    return dict(position=vector(UNITY_BASIS @ matrix.translation),
                forward=vector(UNITY_BASIS @ (matrix.to_3x3() @ Vector((0, 0, -1))).normalized()),
                up=vector(UNITY_BASIS @ (matrix.to_3x3() @ Vector((0, 1, 0))).normalized()))


def sample_camera(scene, camera, frames):
    poses = []
    orthographic_size = 0
    for frame in frames:
        scene.frame_set(frame)
        corners = camera.data.view_frame(scene=scene)
        if camera.data.type == 'ORTHO':
            orthographic_size = max(abs(corner.y) for corner in corners)
            fov = 40
        else:
            tangent = max(abs(corner.y / corner.z) for corner in corners)
            fov = 2 * math.degrees(math.atan(tangent))
        poses.append(dict(frame=frame, fov=fov, **transform_data(camera)))
    return dict(name=camera.name, near=camera.data.clip_start, far=camera.data.clip_end,
                orthographicSize=orthographic_size, poses=poses)


def describe_light(light, set_name):
    data = light.data
    return dict(name=light.name, set=set_name, type=data.type, color=color(data.color),
                energy=data.energy, size=getattr(data, 'size', getattr(data, 'shadow_soft_size', .05)),
                spotAngle=math.degrees(getattr(data, 'spot_size', math.pi / 4)), **transform_data(light))


def describe_material(material):
    shader = next((node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED'), None) \
        if material.node_tree else None
    base_color = material.diffuse_color
    roughness, metallic, emission, strength = material.roughness, material.metallic, (0, 0, 0, 1), 0
    if shader:
        inputs = shader.inputs
        if not inputs['Base Color'].is_linked:
            base_color = inputs['Base Color'].default_value
        roughness = inputs['Roughness'].default_value
        metallic = inputs['Metallic'].default_value
        emission = inputs['Emission Color'].default_value
        strength = inputs['Emission Strength'].default_value
    return dict(name=material.name, color=color(base_color), roughness=roughness, metallic=metallic,
                emissionColor=color(emission), emissionIntensity=strength)


def set_membership(scene, shots):
    visible = {}
    for set_name in dict.fromkeys(shot['set'] for shot in shots):
        frame = next(shot['startFrame'] for shot in shots if shot['set'] == set_name)
        scene.frame_set(frame)
        visible[set_name] = {obj for obj in scene.objects if not obj.hide_render}
    return visible


def write_fbx(scene, output, asset_name, objects, calibration):
    selection = set(objects)
    for obj in objects:
        parent = obj.parent
        while parent is not None:
            selection.add(parent)
            parent = parent.parent
    surroundings = scene.view_layers[0]
    scene.frame_set(scene.frame_start)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selection.union(calibration.objects):
        obj.hide_set(False, view_layer=surroundings)
        obj.select_set(True, view_layer=surroundings)
    surroundings.objects.active = next(iter(calibration.objects))
    destination = output / asset_name
    result = bpy.ops.export_scene.fbx(
        filepath=str(destination), use_selection=True,
        object_types={'ARMATURE', 'MESH', 'EMPTY', 'OTHER'}, use_mesh_modifiers=False,
        add_leaf_bones=False, mesh_smooth_type='FACE', axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', bake_anim=True,
        bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
        bake_anim_step=1.0, bake_anim_simplify_factor=0.5,
    )
    if result != {'FINISHED'} or not destination.is_file():
        raise RuntimeError(f'FBX export failed for {asset_name}: {result}')
    print(f'UNITY PERFORMANCE FBX {asset_name}: {len(selection)} objects, {destination.stat().st_size:,} bytes', flush=True)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--output', type=Path, default=OUTPUT)
    args.add_argument('--asset', action='append', help='Re-export a named FBX alongside the updated edit manifest')
    options = args.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    scene = next(scene for scene in bpy.data.scenes if scene.name.startswith('E01_SC04 | Performance'))
    bpy.context.window.scene = scene
    timeline = json.loads(TIMELINE.read_text(encoding='utf-8'))
    shots = [dict(name=row['id'], set=row['set'], startFrame=row['start_frame'],
                  endFrame=row['end_frame_exclusive'], camera=scene.timeline_markers[row['id']].camera.name)
             for row in timeline['shots']]
    total = timeline['total_frames']
    if scene.frame_start != 0 or scene.frame_end != total - 1 or scene.render.fps != timeline['fps']:
        raise ValueError('The Blender animation and its production edit have different frame ranges or frame rates.')

    visible = set_membership(scene, shots)
    all_visible = set.union(*visible.values())
    objects = {obj for obj in all_visible if obj.type in ASSET_TYPES}
    visibility = []
    for obj in sorted(objects, key=lambda item: item.name):
        sets = [name for name, subset in visible.items() if obj in subset]
        if len(sets) == 1:
            visibility.append(dict(name=obj.name, set=sets[0]))
    lights = []
    for obj in sorted(all_visible, key=lambda item: item.name):
        if obj.type != 'LIGHT':
            continue
        sets = [name for name, subset in visible.items() if obj in subset]
        scene.frame_set(next(shot['startFrame'] for shot in shots if shot['set'] == sets[0]))
        lights.append(describe_light(obj, sets[0] if len(sets) == 1 else ''))

    print('SAMPLING UNITY PERFORMANCE CAMERAS', flush=True)
    cameras = [sample_camera(scene, scene.objects[shot['camera']], range(shot['startFrame'], shot['endFrame']))
               for shot in shots]
    materials = {slot.material for obj in objects for slot in obj.material_slots if slot.material}
    material_rows = [describe_material(item) for item in sorted(materials, key=lambda material: material.name)]
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    calibration = bpy.data.collections.new('Unity axis calibration')
    scene.collection.children.link(calibration)
    add_calibration(calibration)

    groups = {}
    for collection in scene.collection.children:
        if collection.name.startswith('CH_'):
            group = objects.intersection(collection.all_objects)
            if group:
                groups[f'SC04_{collection.name[3:]}.fbx'] = group
    environment = objects.difference(*groups.values())
    groups['SC04_Court.fbx'] = environment.intersection(visible['court'])
    groups['SC04_River.fbx'] = environment.difference(visible['court'])

    requested = options.asset or list(groups)
    for asset_name in requested:
        if asset_name not in groups:
            args.error(f'unknown performance FBX: {asset_name}')
        group = groups[asset_name]
        if not group:
            raise ValueError(f'No objects selected for {asset_name}')
        print(f'BAKING UNITY PERFORMANCE {asset_name}: {len(group)} source objects', flush=True)
        write_fbx(scene, output, asset_name, group, calibration)

    manifest = dict(fps=timeline['fps'], frameCount=total, assets=list(groups), shots=shots,
                    cameras=cameras, materials=material_rows, visibility=visibility, lights=lights)
    (output / 'Performance.json').write_text(json.dumps(manifest, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'UNITY PERFORMANCE EXPORT COMPLETE: {len(groups)} assets, {len(shots)} shots, {total} frames', flush=True)


if __name__ == '__main__':
    main()
