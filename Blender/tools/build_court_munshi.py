"""Build the assistant court scribe (सहायक दरबारी मुंशी) with FBX handoff and renders.

blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_court_munshi.py
"""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character import Character
from build_cast import light, review_floor, setup_stage, stage_camera
import court_munshi


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Characters' / 'Sahayak_Darbari_Munshi'
NAME = 'CH_SahayakDarbariMunshi'


def turn(rig, joint, axis, degrees):
    bone = rig.pose.bones[joint]
    rest = bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = rest.inverted() @ Quaternion(axis, math.radians(degrees)) @ rest


def standing_pose(rig):
    """Arms down and slightly bent, head tipped toward the desk."""
    for side, sign in (('L', 1), ('R', -1)):
        turn(rig, f'upper_arm.{side}', (0,1,0), sign*70)
        turn(rig, f'forearm.{side}', (0,0,1), sign*-14)
        for digit in range(1, 5):
            turn(rig, f'finger_{digit:02d}.{side}', (0,1,0), sign*(18 + digit*4))
    turn(rig, 'head', (1,0,0), 12)
    turn(rig, 'neck', (1,0,0), 6)


def export_fbx(character):
    bpy.ops.object.select_all(action='DESELECT')
    character.rig.select_set(True)
    for part in character.parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = character.rig
    filepath = OUT / f'{NAME}.fbx'
    result = bpy.ops.export_scene.fbx(filepath=str(filepath), use_selection=True,
        object_types={'ARMATURE','MESH'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=False,
        add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE')
    if 'FINISHED' not in result or filepath.stat().st_size < 1024:
        raise RuntimeError(f'FBX export failed: {filepath}')


def stage(character, camera, target, lens, name):
    scene = character.scene
    bpy.context.window.scene = scene
    setup_stage(scene, 1200, 1500, 32, .22)
    review_floor((.041,.055,.061))
    height = court_munshi.SPEC['height']
    stage_camera(scene, name, camera, target, lens)
    light(scene, 'Key', (-2.2,-3.4,3.1), (0,0,height), (1,.85,.72), 360, 2.0)
    light(scene, 'Fill', (2.4,-2.6,2.0), (0,0,height*.9), (.66,.8,1), 120, 2.6)
    light(scene, 'Rim', (1.6,2.2,3.0), (0,0,height), (1,.78,.55), 320, 1.8)
    return scene


def render(scene, camera_name, path):
    scene.camera = bpy.data.objects[camera_name]
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    character = Character(court_munshi.SPEC)
    character.body()
    character.face()
    court_munshi.dress(character)
    character.validate()
    export_fbx(character)
    scene = stage(character, (0,-9.5,1.08), (0,0,1.08), 2.5, 'Full-body camera')
    # Close-up on the two handwritings, looking down the desk slope.
    origin, u_axis, v_axis, n_axis = court_munshi.desk_frame()
    centre = origin + v_axis*.17
    stage_camera(scene, 'Handwriting camera', tuple(centre + n_axis*3), tuple(centre), .75)
    print(f'{character.name}: {len(character.parts)} skinned meshes, '
          f'{len(character.rig.data.bones)} bones', flush=True)
    bpy.context.preferences.filepaths.save_version = 0
    result = bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Sahayak_Darbari_Munshi.blend'), compress=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Could not save the scribe model')
    standing_pose(character.rig)
    render(scene, 'Full-body camera', OUT / 'Sahayak_Darbari_Munshi.png')
    render(scene, 'Handwriting camera', OUT / 'Sahayak_Darbari_Munshi_Handwriting.png')


if __name__ == '__main__':
    main()
