"""Build the assistant palace guard in duty and court costumes, FBX handoffs and renders.

blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_guard.py
"""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character import Character
from build_cast import light, review_floor, setup_stage, stage_camera
import guard


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Characters' / 'Sahayak_Pahredar'
FILES = {'duty': 'CH_SahayakPahredar_Duty', 'court': 'CH_SahayakPahredar_Court'}


def turn(rig, joint, axis, degrees):
    bone = rig.pose.bones[joint]
    rest = bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = rest.inverted() @ Quaternion(axis, math.radians(degrees)) @ rest


def standing_pose(rig, variant):
    """Duty: reporting at the door with the spear grounded. Court: hands at the sides."""
    for side, sign in (('L', 1), ('R', -1)):
        turn(rig, f'upper_arm.{side}', (0,1,0), sign*72)
        turn(rig, f'forearm.{side}', (0,0,1), sign*-10)
        for digit in range(1, 5):
            curl = 55 if (variant == 'duty' and side == 'R') else 14 + digit*3
            turn(rig, f'finger_{digit:02d}.{side}', (0,1,0), sign*curl)
    turn(rig, 'head', (0,0,1), 5 if variant == 'duty' else 0)
    turn(rig, 'neck', (0,1,0), -3)


def export_fbx(character, name):
    bpy.ops.object.select_all(action='DESELECT')
    character.rig.select_set(True)
    for part in character.parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = character.rig
    filepath = OUT / f'{name}.fbx'
    result = bpy.ops.export_scene.fbx(filepath=str(filepath), use_selection=True,
        object_types={'ARMATURE','MESH'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=False,
        add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE')
    if 'FINISHED' not in result or filepath.stat().st_size < 1024:
        raise RuntimeError(f'FBX export failed: {filepath}')


def stage(character):
    scene = character.scene
    bpy.context.window.scene = scene
    setup_stage(scene, 1200, 1500, 32, .22)
    review_floor((.041,.055,.061))
    height = guard.SPEC['height']
    stage_camera(scene, 'Full-body camera', (0,-9.5,1.08), (0,0,1.08), 2.5)
    light(scene, 'Key', (-2.2,-3.4,3.1), (0,0,height), (1,.85,.72), 360, 2.0)
    light(scene, 'Fill', (2.4,-2.6,2.0), (0,0,height*.9), (.66,.8,1), 120, 2.6)
    light(scene, 'Rim', (1.6,2.2,3.0), (0,0,height), (1,.78,.55), 320, 1.8)
    return scene


def build(variant):
    character = Character(guard.spec_for(variant))
    character.body()
    character.face()
    guard.dress(character, variant)
    character.validate()
    export_fbx(character, FILES[variant])
    scene = stage(character)
    print(f'{character.name}: {len(character.parts)} skinned meshes, '
          f'{len(character.rig.data.bones)} bones', flush=True)
    return character, scene


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = {variant: build(variant) for variant in guard.VARIANTS}
    bpy.context.preferences.filepaths.save_version = 0
    result = bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Sahayak_Pahredar.blend'), compress=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Could not save the guard model')
    for variant, (character, scene) in built.items():
        bpy.context.window.scene = scene
        standing_pose(character.rig, variant)
        scene.render.filepath = str(OUT / f'Sahayak_Pahredar_{variant.title()}.png')
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
