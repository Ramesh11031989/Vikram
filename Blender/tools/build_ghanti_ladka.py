"""Build the bell-hearing boy witness, his FBX handoff and a review render.

blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_ghanti_ladka.py
"""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character import Character
from build_cast import aim, light, review_floor, setup_stage, stage_camera
import ghanti_ladka


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Characters' / 'Ghanti_Ladka'


def turn(rig, joint, axis, degrees):
    bone = rig.pose.bones[joint]
    rest = bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = rest.inverted() @ Quaternion(axis, math.radians(degrees)) @ rest


def listening_pose(rig):
    """Relaxed stance, head cocked a little to one side as if listening."""
    for side, sign in (('L', 1), ('R', -1)):
        turn(rig, f'upper_arm.{side}', (0,1,0), sign*74)
        turn(rig, f'forearm.{side}', (0,0,1), sign*-12)
        for digit in range(1, 5):
            turn(rig, f'finger_{digit:02d}.{side}', (0,1,0), sign*(14+digit*3))
    turn(rig, 'head', (0,0,1), 8)
    turn(rig, 'neck', (0,1,0), -5)


def export_fbx(character):
    bpy.ops.object.select_all(action='DESELECT')
    character.rig.select_set(True)
    for part in character.parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = character.rig
    filepath = OUT / 'CH_GhantiLadka.fbx'
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
    height = ghanti_ladka.SPEC['height']
    stage_camera(scene, 'Portrait camera', (0,-7,height*.93), (0,0,height*.93), 1.75)
    light(scene, 'Key', (-2.0,-3.2,2.9), (0,0,height), (1,.85,.72), 330, 2.0)
    light(scene, 'Fill', (2.2,-2.4,1.9), (0,0,height*.9), (.66,.8,1), 110, 2.6)
    light(scene, 'Rim', (1.5,2.0,2.8), (0,0,height), (1,.78,.55), 300, 1.8)
    return scene


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    character = Character(ghanti_ladka.SPEC)
    character.body()
    character.face()
    ghanti_ladka.dress(character)
    ghanti_ladka.childlike_head(character)
    character.validate()
    export_fbx(character)
    scene = stage(character)
    scale = ghanti_ladka.SPEC['height']
    height_m = scale * (1.5 + .312 * ghanti_ladka.HEAD_SCALE)
    print(f'{character.name}: {len(character.parts)} skinned meshes, '
          f'{len(character.rig.data.bones)} bones, about {height_m:.2f} m tall', flush=True)
    bpy.context.preferences.filepaths.save_version = 0
    result = bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Ghanti_Ladka.blend'), compress=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Could not save the boy witness model')
    listening_pose(character.rig)
    scene.render.filepath = str(OUT / 'Ghanti_Ladka_Portrait.png')
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
