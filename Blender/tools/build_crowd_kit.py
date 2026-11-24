"""Build the shared crowd kit (adult man, woman, elder, child): .blend, FBX and review render.

    blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_crowd_kit.py
    blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_crowd_kit.py -- --render

Writes Blender/Characters/Crowd_Kit/Crowd_Kit.blend and one FBX per body;
`--render` also writes CrowdKit_Poses.png.  `--no-save` skips the files.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cast import label, light, review_floor, setup_stage, stage_camera, studio_material
from character import Character
from child import ChildCharacter, add_child_facial_controls, reset_pose, save_pose_asset
import crowd_kit
import crowd_props


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Characters' / 'Crowd_Kit'


def arguments() -> list[str]:
    return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def make_character(spec: dict) -> Character:
    child = spec['name'] == crowd_kit.CHILD_NAME
    character = ChildCharacter(spec) if child else Character(spec)
    character.body()
    character.face()
    crowd_kit.DRESS[spec['name']](character)
    if child:
        add_child_facial_controls(character)
    character.validate()
    stoop = crowd_kit.STOOP[spec['name']]
    for name in crowd_kit.POSE_NAMES:
        pose = crowd_kit.apply_crowd_pose(character.rig, name, stoop)
        save_pose_asset(character.rig, pose, character.name)
    reset_pose(character.rig)
    print(f'{character.name}: {len(character.parts)} skinned meshes, {len(character.rig.data.bones)} bones, '
          f'{len(crowd_kit.POSE_NAMES)} pose assets', flush=True)
    return character


def export_fbx(character: Character) -> None:
    bpy.context.window.scene = character.scene
    bpy.ops.object.select_all(action='DESELECT')
    character.rig.select_set(True)
    for part in character.parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = character.rig
    path = OUT / f'CH_{character.name}.fbx'
    result = bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=False, add_leaf_bones=False,
        bake_anim=False, mesh_smooth_type='FACE', use_custom_props=True)
    if 'FINISHED' not in result or path.stat().st_size < 1024:
        raise RuntimeError(f'FBX export failed: {path}')


def display_copy(scene, character: Character, label_text: str, location, yaw: float) -> bpy.types.Object:
    group = bpy.data.collections.new(f'{character.name} • {label_text}')
    scene.collection.children.link(group)
    rig = character.rig.copy()
    rig.name = f'{character.name} • {label_text} rig'
    rig.show_in_front = False
    group.objects.link(rig)
    for part in character.parts:
        clone = part.copy()
        group.objects.link(clone)
        clone.parent = rig
        clone.modifiers['Character Skinning'].object = rig
    rig.location = location
    rig.rotation_euler.z = math.radians(yaw)
    return rig


def hold(obj: bpy.types.Object, rig: bpy.types.Object, bone: str) -> None:
    """Keep `obj` where it is in the world but follow `bone` (a Child Of with the matching inverse)."""
    constraint = obj.constraints.new('CHILD_OF')
    constraint.target, constraint.subtarget = rig, bone
    bpy.context.view_layer.update()
    constraint.set_inverse_pending = False
    constraint.inverse_matrix = (rig.matrix_world @ rig.pose.bones[bone].matrix).inverted()


def place(obj: bpy.types.Object, origin: Vector, offset: Vector, yaw: float) -> None:
    """Put `obj` at `origin + offset`, with the offset turned by the same yaw as the display rig."""
    obj.location = origin + Matrix.Rotation(math.radians(yaw), 3, 'Z') @ offset
    obj.rotation_euler.z = math.radians(yaw)


def dress_pose(scene, character: Character, pose_name: str, x: float, yaw: float) -> bpy.types.Object:
    """One posed display copy with the prop its pose uses (diya, mat or steps)."""
    bpy.context.window.scene = scene
    rig = display_copy(scene, character, pose_name, (x, 0, 0), yaw)
    group = rig.users_collection[0]
    origin = Vector((x, 0, 0))
    crowd_kit.apply_crowd_pose(rig, pose_name, crowd_kit.STOOP[character.name])
    if pose_name == 'Hold diya':
        hands = [rig.pose.bones[f'hand.{side}'] for side in 'LR']
        centre = rig.matrix_world @ ((hands[0].head + hands[0].tail + hands[1].head + hands[1].tail) / 4)
        diya = crowd_props.build(group)
        diya.location = centre - Vector((0, 0, .012))
        hold(diya, rig, 'hand.R')
    elif pose_name == 'Spread mat':
        mat = crowd_props.mat(group, length=1.0, width=.85)
        place(mat, origin, Vector((0, -.12, 0)), yaw)
        rig.location.z = .008
    elif pose_name == 'Wait on steps':
        steps = crowd_props.stairs(group, crowd_kit.SEAT_RISE, steps=2, width=1.0)
        place(steps, origin, Vector((0, 0, 0)), yaw)
        rig.location = origin + Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Vector((0, .17, 0))
    return rig


def render_pose(characters: list[Character], pose_name: str) -> None:
    scene = bpy.data.scenes.new(f'Crowd kit • {pose_name}')
    setup_stage(scene, 1800, 800, 24, .2)
    review_floor((.045, .052, .058))
    lettering = studio_material('Labels • Warm sandstone', (.55, .47, .34))
    camera = stage_camera(scene, 'Review camera', (0, -7, .85), (0, 0, .85), 5.8)
    camera.rotation_euler.x = math.radians(84)
    camera.location.z = 1.25
    light(scene, 'Key', (-2.4, -3.4, 3.6), (0, 0, .6), (1, .86, .72), 330, 2.2)
    light(scene, 'Fill', (2.6, -2.6, 1.8), (0, 0, .6), (.70, .82, 1), 90, 2.8)
    light(scene, 'Warm rim', (2.0, 2.4, 2.6), (0, 0, .75), (1, .78, .56), 280, 1.8)
    light(scene, 'Cool rim', (-2.2, 1.8, 2.2), (0, 0, .7), (.55, .72, 1), 140, 2.0)
    for index, character in enumerate(characters):
        x = (index - 1.5) * 1.3
        dress_pose(scene, character, pose_name, x, -35)
        label(scene, f'{character.name} label', character.name.removeprefix('Crowd').upper(), x, -.04, .07,
              lettering, camera, -.6)
    label(scene, 'Pose label', pose_name.upper(), 0, 1.95, .09, lettering, camera, -.6)
    slug = pose_name.replace(' ', '_')
    scene.render.filepath = str(OUT / f'CrowdKit_{slug}.png')
    bpy.context.window.scene = scene
    bpy.ops.render.render(write_still=True)
    print(f'Rendered CrowdKit_{slug}.png', flush=True)


def main() -> None:
    args = arguments()
    startup = bpy.context.scene
    OUT.mkdir(parents=True, exist_ok=True)
    characters = [make_character(spec) for spec in crowd_kit.SPECS]
    if startup not in {c.scene for c in characters}:
        bpy.data.scenes.remove(startup)
    if '--no-save' not in args:
        for character in characters:
            export_fbx(character)
        bpy.context.window.scene = characters[0].scene
        bpy.context.preferences.filepaths.save_version = 0
        result = bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Crowd_Kit.blend'), compress=True)
        if 'FINISHED' not in result:
            raise RuntimeError('Could not save the crowd kit')
    if '--render' in args:
        for name in crowd_kit.POSE_NAMES:
            render_pose(characters, name)


if __name__ == '__main__':
    main()
