"""Build the anonymous red-cloth figure at the chowki: .blend, FBX and review renders.

blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_anonymous_red_cloth.py
"""

import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character import Character
from build_cast import aim, light, review_floor, setup_stage, studio_material
import anonymous_red_cloth as figure_spec


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Characters' / 'Anonymous_Red_Cloth'
NAME = figure_spec.SPEC['name']
FACE_WORDS = ('Eye', 'Brow', 'Nostril', 'Mouth', 'Lips', 'Ear', 'Iris')


def turn(rig, joint, axis, degrees):
    bone = rig.pose.bones[joint]
    rest = bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = rest.inverted() @ Quaternion(axis, math.radians(degrees)) @ rest


def standing_pose(rig):
    """Relaxed stance with the head turned a little toward the lamp."""
    for side, sign in (('L', 1), ('R', -1)):
        turn(rig, f'upper_arm.{side}', (0,1,0), sign*76)
        turn(rig, f'forearm.{side}', (0,0,1), sign*-8)
        for digit in range(1, 5):
            turn(rig, f'finger_{digit:02d}.{side}', (0,1,0), sign*(14+digit*3))
    turn(rig, 'head', (0,0,1), -28)
    turn(rig, 'neck', (0,0,1), -10)
    turn(rig, 'chest', (0,0,1), -6)


def check_no_face(character):
    """The shot must not reveal an identity, so no facial geometry may exist."""
    faces = [obj.name for obj in character.parts
             if any(word in obj.name.partition('_')[2] for word in FACE_WORDS)]
    shaped = [obj.name for obj in character.parts if obj.data.shape_keys]
    if faces or shaped:
        raise ValueError(f'Facial parts or mouth shapes present: {faces + shaped}')
    return {'facial_meshes': 0, 'shape_keys': 0}


def export_fbx(character):
    bpy.ops.object.select_all(action='DESELECT')
    character.rig.select_set(True)
    for part in character.parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = character.rig
    filepath = OUT / f'CH_{character.name}.fbx'
    result = bpy.ops.export_scene.fbx(filepath=str(filepath), use_selection=True,
        object_types={'ARMATURE','MESH'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=False,
        add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE')
    if 'FINISHED' not in result or filepath.stat().st_size < 1024:
        raise RuntimeError(f'FBX export failed: {filepath}')


def add_camera(scene, name, location, target, lens):
    data = bpy.data.cameras.new(name)
    data.lens, data.clip_start, data.clip_end = lens, .03, 60
    camera = bpy.data.objects.new(name, data)
    scene.collection.objects.link(camera)
    camera.location = location
    aim(camera, target)
    return camera


def stage(scene):
    """Night ghat: lamp-lit chowki with a dark, cool fill."""
    setup_stage(scene, 1500, 1500, 48, .06)
    scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (.03,.05,.08,1)
    review_floor((.028,.034,.040))
    wood = studio_material('Chowki • aged teak', (.15,.069,.026), .66)
    clay = studio_material('Chowki • clay lamp', (.22,.085,.04), .8)
    flame = studio_material('Chowki • flame', (1,.34,.045), .4)
    shader = flame.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Emission Color'].default_value = (1,.34,.045,1)
    shader.inputs['Emission Strength'].default_value = 7
    figure_spec.chowki_props(scene, wood, clay, flame)
    light(scene, 'Cool river fill', (-2.5,2.2,2.6), (0,0,1.0), (.45,.62,1), 70, 3.0)
    light(scene, 'Soft moon rim', (2.4,-2.2,2.4), (0,0,1.2), (.5,.66,1), 55, 2.0)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = figure_spec.SPEC
    character = Character(spec)
    character.body()
    figure_spec.dress(character)
    character.validate()
    face_report = check_no_face(character)
    export_fbx(character)
    scene = character.scene
    stage(scene)
    back = add_camera(scene, 'Back and shoulder camera', (.30,1.45,1.28), (.05,0,1.16), 62)
    wide = add_camera(scene, 'Back three-quarter camera', (1.35,1.35,1.30), (.25,0,1.0), 48)
    front = add_camera(scene, 'Front privacy check camera', (0,-2.0,1.45), (0,0,1.3), 55)
    scene.camera = back
    bpy.context.preferences.filepaths.save_version = 0
    result = bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Anonymous_Red_Cloth.blend'), compress=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Could not save the anonymous red-cloth model')
    standing_pose(character.rig)
    bpy.context.window.scene = scene
    renders = (('Anonymous_Red_Cloth_Back_Shoulder.png', back),
               ('Anonymous_Red_Cloth_Three_Quarter.png', wide),
               ('Anonymous_Red_Cloth_Front_Check.png', front))
    for filename, camera in renders:
        scene.camera = camera
        scene.render.filepath = str(OUT / filename)
        bpy.ops.render.render(write_still=True, scene=scene.name)
    report = {'character': NAME, 'rig_bones': len(character.rig.data.bones),
              'skinned_meshes': len(character.parts),
              'polygons': sum(len(obj.data.polygons) for obj in character.parts),
              'height_m': round(1.812*spec['height'], 2), **face_report,
              'red_cloth': 'Red cloth over shoulders', 'fbx': f'CH_{NAME}.fbx',
              'renders': [name for name, _ in renders]}
    (OUT / 'Anonymous_Red_Cloth_Check.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
