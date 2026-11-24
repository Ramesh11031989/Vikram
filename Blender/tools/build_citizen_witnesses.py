"""Build the two citizen witnesses on the shared rig: .blend, FBX and review renders.

blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_citizen_witnesses.py
"""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character import Character
from build_cast import light, review_floor, setup_stage, stage_camera
import citizen_witnesses


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Characters' / 'Citizen_Witnesses'


def turn(rig, joint, axis, degrees):
    bone = rig.pose.bones[joint]
    rest = bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = rest.inverted() @ Quaternion(axis, math.radians(degrees)) @ rest


def standing_pose(rig, head_turn):
    """Relaxed arms-down stance, shared by both forms; only the head angle differs."""
    for side, sign in (('L', 1), ('R', -1)):
        turn(rig, f'upper_arm.{side}', (0,1,0), sign*72)
        turn(rig, f'forearm.{side}', (0,0,1), sign*-10)
        for digit in range(1, 5):
            turn(rig, f'finger_{digit:02d}.{side}', (0,1,0), sign*(12+digit*3))
    turn(rig, 'head', (0,0,1), head_turn)


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


def stage(scene, width, camera_x, camera_width, height):
    setup_stage(scene, width, 1500, 32, .22)
    review_floor((.041,.055,.061))
    stage_camera(scene, 'Review camera', (camera_x,-8,height*.52), (camera_x,0,height*.52), camera_width)
    light(scene, 'Key', (camera_x-2.0,-3.2,2.9), (camera_x,0,height*.6), (1,.85,.72), 330, 2.0)
    light(scene, 'Fill', (camera_x+2.2,-2.4,1.9), (camera_x,0,height*.5), (.66,.8,1), 110, 2.6)
    light(scene, 'Rim', (camera_x+1.5,2.0,2.8), (camera_x,0,height*.6), (1,.78,.55), 300, 1.8)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cast = []
    for spec in citizen_witnesses.SPECS:
        character = Character(spec)
        character.body()
        character.face()
        citizen_witnesses.DRESS[spec['name']](character)
        character.validate()
        export_fbx(character)
        stage(character.scene, 1200, 0, 2.15, 1.85*spec['height'])
        cast.append(character)
        print(f'{character.name}: {len(character.parts)} skinned meshes, '
              f'{len(character.rig.data.bones)} bones, about {1.812*spec["height"]:.2f} m tall', flush=True)
    bpy.context.preferences.filepaths.save_version = 0
    result = bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Citizen_Witnesses.blend'), compress=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Could not save the citizen witness models')
    for character, head_turn in zip(cast, (-6, 7)):
        standing_pose(character.rig, head_turn)
        character.scene.render.filepath = str(OUT / f'{character.name}_Portrait.png')
        bpy.context.window.scene = character.scene
        bpy.ops.render.render(write_still=True, scene=character.scene.name)

    # Side-by-side comparison; the rigs move only after the .blend was saved.
    lineup = bpy.data.scenes.new('Citizen Witnesses | Lineup')
    for character, x in zip(cast, (-.45, .45)):
        lineup.collection.children.link(character.collection)
        character.rig.location.x = x
    bpy.context.window.scene = lineup
    stage(lineup, 1600, 0, 2.3, 1.85)
    lineup.render.resolution_y = 1500
    lineup.render.filepath = str(OUT / 'Citizen_Witnesses_Lineup.png')
    bpy.ops.render.render(write_still=True, scene=lineup.name)


if __name__ == '__main__':
    main()
