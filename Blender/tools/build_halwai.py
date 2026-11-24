"""Build the Halwai (rooftop witness): editable .blend, FBX handoff, check report and review renders.

    blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_halwai.py
    blender ... --python Blender/tools/build_halwai.py -- --quick       # fast, noisy review renders
    blender ... --python Blender/tools/build_halwai.py -- --no-render   # build and export only

Writes Blender/Halwai.blend, Blender/Exports/CH_Halwai.fbx, Blender/Exports/CH_Halwai_Check.json
and Blender/Previews/Halwai_*.png. Touches no other cast file.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Callable

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cast as stage
from civilian import Civilian
import facial_controls
import halwai


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / 'Halwai.blend'
FBX = ROOT / 'Exports' / 'CH_Halwai.fbx'
CHECK = ROOT / 'Exports' / 'CH_Halwai_Check.json'
PREVIEWS = ROOT / 'Previews'
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
QUICK = '--quick' in ARGS


def make_halwai() -> tuple[Civilian, dict[str, int]]:
    character = Civilian(halwai.SPEC)
    character.body()
    character.face()
    halwai.dress(character)
    stats = halwai.groom(character)
    halwai.finish(character)
    facial_controls.add_facial_controls(character)
    halwai.extend_facial_controls(character)
    character.scale_head(character.spec.get('head_scale', 1.0))
    character.validate()
    character.rig['Witness'] = ('Halwai, rooftop witness (chapter 1). Poses: halwai.relaxed_pose, '
                                'halwai.pointing_pose(yaw, pitch). Facial controls as the main cast.')
    stage.select_rig(character)
    print(f'Halwai: {len(character.parts)} skinned meshes, {len(character.rig.data.bones)} bones', flush=True)
    return character, stats


def export_fbx(character: Civilian) -> None:
    stage.select_rig(character)
    for part in character.parts:
        part.select_set(True)
    FBX.parent.mkdir(exist_ok=True)
    result = bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=False, add_leaf_bones=False,
        bake_anim=False, mesh_smooth_type='FACE', use_custom_props=True)
    if 'FINISHED' not in result or FBX.stat().st_size < 1024:
        raise RuntimeError(f'FBX export failed: {FBX}')
    stage.select_rig(character)


def retarget_drivers(data, source, target) -> None:
    keys = getattr(data, 'shape_keys', None)
    if keys is None or keys.animation_data is None:
        return
    for curve in keys.animation_data.drivers:
        for variable in curve.driver.variables:
            for item in variable.targets:
                if item.id == source:
                    item.id = target


def posed_copy(scene, character: Civilian, label: str, pose: Callable[[object], None],
               location: tuple[float, float, float] = (0, 0, 0), yaw: float = 0,
               expressive: bool = False):
    """A display duplicate. Expressive copies own their shape-key meshes so face controls stay local."""
    collection = bpy.data.collections.new(f'Halwai • {label}')
    scene.collection.children.link(collection)
    rig = character.rig.copy()
    rig.data = character.rig.data
    rig.name = f'Halwai • {label} rig'
    rig.show_in_front = False
    collection.objects.link(rig)
    for part in character.parts:
        clone = part.copy()
        if expressive and part.data.shape_keys is not None:
            clone.data = part.data.copy()
            retarget_drivers(clone.data, character.rig, rig)
        collection.objects.link(clone)
        clone.parent = rig
        clone.modifiers['Character Skinning'].object = rig
    rig.location = location
    rig.rotation_euler.z = math.radians(yaw)
    pose(rig)
    return rig


def perspective_camera(scene, name: str, location, target, lens: float):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_width = 36
    camera = bpy.data.objects.new(name, data)
    scene.collection.objects.link(camera)
    camera.location = location
    stage.aim(camera, target)
    scene.camera = camera
    return camera


def backdrop(scene, color=(.046, .040, .038)) -> None:
    """A curved sweep like a photo cove so the floor fades into the wall."""
    bpy.context.window.scene = scene
    verts, faces = [], []
    columns = 2
    for i in range(25):
        t = i / 24
        y = -14 + 17.5 * t if t < .5 else 3.5 + 2.5 * math.sin((t - .5) * math.pi)
        z = 0 if t < .5 else 2.5 * (1 - math.cos((t - .5) * math.pi))
        if t == 1:
            z = 14
        for x in (-12, 12):
            verts.append((x, y, z))
    for i in range(24):
        a = i * columns
        faces.append((a, a + 1, a + 3, a + 2))
    mesh = bpy.data.meshes.new('Review sweep')
    mesh.from_pydata(verts, [], faces)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new('Review sweep', mesh)
    scene.collection.objects.link(obj)
    obj.data.materials.append(stage.studio_material(f'{scene.name} • Sweep', color, .9))


def portrait_lights(scene, target: tuple[float, float, float], scale: float = 1.0) -> None:
    """Warm side key (Rembrandt), low cool fill, two rims: shows the sculpted form of the face."""
    tx, ty, tz = target
    stage.light(scene, 'Warm key', (tx - 1.9 * scale, ty - 1.3 * scale, tz + 1.1 * scale), target, (1, .85, .70), 230 * scale ** 2, .9 * scale)
    stage.light(scene, 'Cool fill', (tx + 1.8 * scale, ty - 1.6 * scale, tz + .1 * scale), target, (.70, .82, 1), 34 * scale ** 2, 2.4 * scale)
    stage.light(scene, 'Rim', (tx + 1.2 * scale, ty + 1.6 * scale, tz + .9 * scale), target, (1, .80, .62), 300 * scale ** 2, .8 * scale)
    stage.light(scene, 'Hair rim', (tx - 1.1 * scale, ty + 1.4 * scale, tz + 1.3 * scale), target, (.75, .85, 1), 140 * scale ** 2, .8 * scale)


def samples(full: int) -> int:
    return max(16, full // 5) if QUICK else full


def size(width: int, height: int) -> tuple[int, int]:
    return (int(width * .6), int(height * .6)) if QUICK else (width, height)


Shot = tuple[object, object, str, tuple[int, int]]


def turnaround(character: Civilian) -> list[Shot]:
    scene = bpy.data.scenes.new('Halwai • Turnaround')
    stage.setup_stage(scene, *size(2200, 1200), samples(96), .18)
    backdrop(scene)
    for index, yaw in enumerate((0, -38, -90, 180)):
        posed_copy(scene, character, f'Turnaround {yaw}', halwai.relaxed_pose, ((index - 1.5) * .78, 0, 0), yaw)
    camera = stage.stage_camera(scene, 'Turnaround camera', (0, -9, .84), (0, 0, .84), 3.30)
    stage.light(scene, 'Warm key', (-3.2, -4.4, 4.6), (0, 0, 1.0), (1, .86, .72), 900, 3.0)
    stage.light(scene, 'Cool fill', (3.4, -3.0, 2.2), (0, 0, .9), (.70, .82, 1), 220, 4.0)
    stage.light(scene, 'Warm rim', (2.6, 3.0, 3.8), (0, 0, 1.1), (1, .78, .58), 700, 2.4)
    stage.light(scene, 'Cool rim', (-2.6, 2.4, 3.0), (0, 0, 1.1), (.62, .78, 1), 380, 2.4)
    return [(scene, camera, 'Halwai_Turnaround.png', size(2200, 1200))]


def portrait(character: Civilian) -> list[Shot]:
    scene = bpy.data.scenes.new('Halwai • Portrait')
    stage.setup_stage(scene, *size(1200, 1500), samples(192), .10)
    backdrop(scene)
    posed_copy(scene, character, 'Portrait', halwai.relaxed_pose, (0, 0, 0), -22)
    head = (0, -.03, 1.50)
    three_quarter = perspective_camera(scene, 'Portrait camera', (.36, -1.30, 1.53), head, 85)
    front = perspective_camera(scene, 'Front portrait camera', (.47, -1.12, 1.51), (0, -.03, 1.49), 85)
    portrait_lights(scene, head, .8)
    scene.camera = three_quarter
    return [(scene, three_quarter, 'Halwai_Portrait.png', size(1200, 1500)),
            (scene, front, 'Halwai_Portrait_Front.png', size(1200, 1500))]


def pointing(character: Civilian) -> list[Shot]:
    scene = bpy.data.scenes.new('Halwai • Pointing')
    stage.setup_stage(scene, *size(1400, 1600), samples(128), .14)
    backdrop(scene)
    posed_copy(scene, character, 'Pointing', lambda rig: halwai.pointing_pose(rig), (0, 0, 0), 0, expressive=True)
    wide = perspective_camera(scene, 'Pointing camera', (1.30, -3.15, 1.15), (-.20, 0, .92), 42)
    close = perspective_camera(scene, 'Pointing close camera', (.95, -1.55, 1.42), (-.22, -.18, 1.33), 50)
    portrait_lights(scene, (0, 0, 1.15), 1.6)
    scene.camera = wide
    return [(scene, wide, 'Halwai_Pointing.png', size(1400, 1600)),
            (scene, close, 'Halwai_Pointing_Close.png', size(1600, 1000))]


def rooftop(character: Civilian) -> list[Shot]:
    """Readability at story distance: he stands on his roof and points across the mandi at dawn."""
    scene = bpy.data.scenes.new('Halwai • Rooftop read')
    stage.setup_stage(scene, *size(1600, 900), samples(96), .9)
    world = scene.world.node_tree.nodes.get('Background')
    world.inputs['Color'].default_value = (.36, .45, .62, 1)
    plaster = stage.studio_material('Rooftop • Lime plaster', (.42, .36, .29), .95)
    brick = stage.studio_material('Rooftop • Old brick', (.22, .11, .07), .9)
    ground = stage.studio_material('Rooftop • Wet earth', (.08, .07, .055), .6)

    def block(name: str, centre, dims, material) -> None:
        bpy.ops.mesh.primitive_cube_add(location=centre)
        obj = bpy.context.object
        obj.name = name
        obj.scale = (dims[0] / 2, dims[1] / 2, dims[2] / 2)
        obj.data.materials.append(material)
    bpy.context.window.scene = scene
    block('Halwai house', (0, 1.0, -1.9), (4.2, 4.2, 3.8), plaster)
    block('Parapet', (0, -1.05, .27), (4.2, .18, .54), plaster)
    block('Parapet coping', (0, -1.05, .56), (4.3, .26, .05), brick)
    block('Neighbour roof', (5.2, 1.4, -1.5), (3.6, 4.0, 4.6), plaster)
    block('Street', (0, -8, -3.82), (60, 30, .05), ground)
    posed_copy(scene, character, 'Rooftop', lambda rig: halwai.pointing_pose(rig, yaw=58, pitch=-12),
               (0, -.2, 0), 18, expressive=True)
    camera = perspective_camera(scene, 'Street camera', (6.5, -15.5, -1.9), (0, 0, .7), 50)
    sun = bpy.data.lights.new('Dawn sun', 'SUN')
    sun.energy, sun.color, sun.angle = 3.2, (1, .74, .52), math.radians(2)
    sun_obj = bpy.data.objects.new('Dawn sun', sun)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(68), 0, math.radians(-62))
    scene.view_settings.exposure = -.4
    return [(scene, camera, 'Halwai_Rooftop_Read.png', size(1600, 900))]


def compare_with_cast() -> None:
    """Side-by-side with Gopal from the existing cast library, for scale and style review only."""
    import gopal
    halwai_rig = bpy.data.objects['Halwai_Rig']
    character = stage.make_character(gopal)
    scene = bpy.data.scenes.new('Halwai • With Gopal')
    stage.setup_stage(scene, *size(1600, 1100), samples(96), .18)
    backdrop(scene)
    source = Civilian.__new__(Civilian)
    source.rig = halwai_rig
    source.parts = [obj for obj in bpy.data.collections['CH_Halwai'].objects if obj.type == 'MESH']
    posed_copy(scene, source, 'Beside Gopal', halwai.relaxed_pose, (-.42, 0, 0), -8)
    rig = stage.showcase_character(scene, character, .42, 8)
    rig.location.z = 0
    camera = stage.stage_camera(scene, 'Comparison camera', (0, -9, .97), (0, 0, .97), 2.95)
    stage.light(scene, 'Warm key', (-3.2, -4.4, 4.6), (0, 0, 1.0), (1, .86, .72), 900, 3.0)
    stage.light(scene, 'Cool fill', (3.4, -3.0, 2.2), (0, 0, .9), (.70, .82, 1), 220, 4.0)
    stage.light(scene, 'Warm rim', (2.6, 3.0, 3.8), (0, 0, 1.1), (1, .78, .58), 700, 2.4)
    render((scene, camera, 'Halwai_with_Gopal.png', size(1600, 1100)))


def render(shot: Shot) -> None:
    scene, camera, name, (width, height) = shot
    bpy.context.window.scene = scene
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.filepath = str(PREVIEWS / name)
    PREVIEWS.mkdir(exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print(f'Rendered {scene.render.filepath}', flush=True)


def round_trip(character_stats: dict[str, int]) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    mouth = next(obj for obj in meshes if obj.name.endswith('_Mouth'))
    bones = sorted(bone.name for bone in rigs[0].data.bones)
    report = {
        'status': 'PASS', 'character': 'Halwai', 'file': FBX.name, 'bytes': FBX.stat().st_size,
        'bones': len(bones), 'shared_cast_bones_present': all(name in bones for name in (
            'root', 'hips', 'spine', 'chest', 'neck', 'head', 'upper_arm.R', 'forearm.R', 'hand.R',
            'finger_01.R', 'thumb.R', 'thigh.L', 'shin.L', 'foot.L', 'toes.L', 'eye.L')),
        'finger_joints': [name for name in bones if name.endswith(('_mid.R', '_tip.R'))],
        'meshes': len(meshes), 'mouth_shapes': list(mouth.data.shape_keys.key_blocks.keys()),
        'groom_strands': character_stats,
        'limits': 'Neutral rest pose. Blender custom-property drivers, procedural textile, check and '
                  'skin-tint shaders need rebinding or baking in the destination.',
    }
    if len(rigs) != 1 or len(bones) != 52 or not report['shared_cast_bones_present']:
        report['status'] = 'FAIL'
    if len(report['mouth_shapes']) < 11:
        report['status'] = 'FAIL'
    CHECK.write_text(json.dumps(report, indent=2) + '\n')
    if report['status'] != 'PASS':
        raise RuntimeError(f'Round trip failed: {report}')
    return report


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    empty = bpy.context.scene
    character, stats = make_halwai()
    export_fbx(character)
    shots = turnaround(character) + portrait(character) + pointing(character) + rooftop(character)
    bpy.data.scenes.remove(empty)
    stage.configure_view(shots[0][0], camera=True)
    bpy.context.preferences.filepaths.save_version = 0
    result = bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Could not save Halwai.blend')
    if '--no-render' not in ARGS:
        only = [arg.removeprefix('--only=') for arg in ARGS if arg.startswith('--only=')]
        for shot in shots:
            if not only or any(key.lower() in shot[2].lower() for key in only):
                render(shot)
    if '--compare' in ARGS:
        compare_with_cast()
    report = round_trip(stats)
    print('HALWAI_BUILD_PASS', json.dumps({k: report[k] for k in ('bones', 'meshes', 'bytes')}), flush=True)


if __name__ == '__main__':
    main()
