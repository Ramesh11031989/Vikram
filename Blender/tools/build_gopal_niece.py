"""Build Gopal's niece: editable .blend, FBX handoff and review renders.

    blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_gopal_niece.py
    blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_gopal_niece.py -- --renders

The first command writes Blender/Characters/Gopal_Niece/Gopal_Niece.blend and
CH_GopalNiece.fbx; `--renders` also renders the previews beside them.
`--only NAME` renders a single preview (turnaround, portrait, boat) and
`--no-save` skips the .blend and FBX.  The rig, face and pose tools come from
`child.py`, shared with Nandu's daughter.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cast import label, light, review_floor, setup_stage, stage_camera, studio_material
from child import ChildCharacter, add_child_facial_controls, apply_pose, reset_pose, save_pose_asset
import build_nandu_daughter as shared
import gopal_niece


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Characters' / 'Gopal_Niece'
BLEND = OUT / 'Gopal_Niece.blend'
FBX = OUT / 'CH_GopalNiece.fbx'


def make_character() -> ChildCharacter:
    character = ChildCharacter(gopal_niece.SPEC)
    character.body()
    character.face()
    gopal_niece.dress(character)
    add_child_facial_controls(character)
    character.validate()
    rig = character.rig
    for pose in gopal_niece.POSES:
        apply_pose(rig, pose)
        save_pose_asset(rig, pose, character.name)
    reset_pose(rig)
    print(f'{character.name}: {len(character.parts)} skinned meshes, {len(rig.data.bones)} bones, '
          f'{len(gopal_niece.POSES)} pose assets', flush=True)
    return character


def pose_named(name: str):
    return next(pose for pose in gopal_niece.POSES if pose.name == name)


def render(scene, filename: str) -> None:
    bpy.context.window.scene = scene
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)
    print(f'Rendered {filename}', flush=True)


def export_fbx(character: ChildCharacter) -> None:
    shared.FBX = FBX  # the shared exporter writes to its module-level path
    shared.export_fbx(character)


def lowest(rig_copy, words: tuple[str, ...]) -> float:
    """Lowest evaluated world-space z of the skinned parts whose names contain any of `words`."""
    graph = bpy.context.evaluated_depsgraph_get()
    low = 1e9
    for obj in rig_copy.users_collection[0].objects:
        if obj.type == 'MESH' and any(word in obj.name for word in words):
            mesh = obj.evaluated_get(graph)
            low = min(low, min((mesh.matrix_world @ Vector(c)).z for c in mesh.bound_box))
    return low


# ------------------------------------------------------------- review stage
def backdrop(size: float, y: float) -> None:
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, y, 1), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(studio_material('Backdrop • Charcoal', (.035, .04, .047)))


def turnaround(character: ChildCharacter) -> None:
    scene = bpy.data.scenes.new('Niece • Turnaround')
    setup_stage(scene, 1600, 1000, 24, .2)
    review_floor((.045, .052, .058))
    lettering = studio_material('Labels • Warm sandstone', (.55, .47, .34))
    camera = stage_camera(scene, 'Turnaround camera', (0, -7, .56), (0, 0, .52), 2.4)
    light(scene, 'Key', (-2.4, -3.4, 3.6), (0, 0, .55), (1, .86, .72), 260, 2.0)
    light(scene, 'Fill', (2.4, -2.6, 1.8), (0, 0, .55), (.70, .82, 1), 70, 2.6)
    light(scene, 'Warm rim', (2.0, 2.4, 2.6), (0, 0, .7), (1, .78, .56), 240, 1.8)
    light(scene, 'Cool rim', (-2.2, 1.8, 2.2), (0, 0, .65), (.55, .72, 1), 120, 2.0)
    stand = pose_named('Stand')
    for index, (yaw, text) in enumerate(((0, 'FRONT'), (-35, 'THREE-QUARTER'), (-90, 'SIDE'), (180, 'BACK'))):
        x = -.93 + index * .62
        shared.display_copy(scene, character, text.title(), (x, 0, 0), yaw, stand)
        label(scene, f'{text} label', text, x, .04, .042, lettering, camera, -.6)
    label(scene, 'Height label', "GOPAL'S NIECE  •  1.00 m  •  CHILD RIG", 0, 1.1, .045, lettering, camera, -.6)
    render(scene, 'GopalNiece_Turnaround.png')


def portrait(character: ChildCharacter) -> None:
    scene = bpy.data.scenes.new('Niece • Portrait')
    setup_stage(scene, 1800, 820, 40, .16)
    review_floor((.03, .036, .042))
    backdrop(6, 1.2)
    stand = pose_named('Stand')
    z = character.rig.data.bones['eye.L'].head_local.z - .03
    camera = stage_camera(scene, 'Portrait camera', (0, -4, z), (0, 0, z), .62)
    camera.data.type = 'PERSP'
    camera.data.lens = 135
    camera.location = (0, -2.55, z + .015)
    light(scene, 'Portrait key', (-1.1, -1.5, z + 1.0), (0, 0, z), (1, .85, .72), 80, .9)
    light(scene, 'Portrait fill', (1.3, -1.3, z + .3), (0, 0, z), (.68, .8, 1), 28, 1.3)
    light(scene, 'Hair rim', (.9, 1.2, z + .8), (0, 0, z + .05), (1, .8, .6), 70, .8)
    light(scene, 'Cool rim', (-1.0, .9, z + .5), (0, 0, z), (.6, .75, 1), 40, .8)
    for x, yaw, name in ((-.225, 0, 'front'), (0, -38, 'three-quarter'), (.215, -90, 'profile')):
        shared.display_copy(scene, character, f'Portrait {name}', (x, 0, 0), yaw, stand)
    render(scene, 'GopalNiece_Portrait.png')


def box(scene, name: str, center, size, material, yaw: float = 0) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    obj.rotation_euler.z = math.radians(yaw)
    obj.data.materials.append(material)
    return obj


def boat_scene(character: ChildCharacter) -> None:
    """E01_SC04_SH09 reference: she sits on the thwart, right hand trailing over the gunwale into the water."""
    scene = bpy.data.scenes.new('Niece • In the boat')
    setup_stage(scene, 1200, 700, 12, .2)
    backdrop(10, 3.5)
    lettering = studio_material('Labels • Warm sandstone', (.55, .47, .34))
    wood = studio_material('River skiff • Weathered planks', (.20, .125, .07), .85)
    water = studio_material('River • Night water', (.018, .045, .06), .12)
    rig = shared.display_copy(scene, character, 'In the boat', (0, 0, 0), 0, pose_named('Hand in water'))
    bpy.context.view_layer.update()
    tip = lowest(rig, ('Finger', 'Thumb'))  # fingertips of the trailing hand
    rig.location.z = -tip  # the water surface is z = 0, exactly at her fingertips
    bpy.context.view_layer.update()
    floor_top = lowest(rig, ('Foot', 'Toe', 'Instep'))  # bare soles on the floor boards
    seat_top = lowest(rig, ('frock', 'Frock')) + .012  # the frock hem rests on the thwart
    reach = [rig.matrix_world @ Vector(c) for o in rig.users_collection[0].objects
             if o.type == 'MESH' and 'Finger' in o.name for c in o.bound_box]
    hand_x = min(p.x for p in reach)
    wall_x = hand_x + .075  # the right gunwale lies between her shoulder and her hand
    gunwale_top = floor_top + .17
    hull_bottom = -.12  # the planking runs below the water line, so the river laps the outside only
    middle = (hull_bottom + gunwale_top) / 2
    box(scene, 'Skiff floor boards', (0, 0, floor_top - .015), (1.0, 1.5, .03), wood)
    box(scene, 'Skiff thwart', (.10, .02, seat_top - .015), (.62, .20, .03), wood)
    # No right gunwale is modelled: her arm passes over it, and the skiff prop in gopal_hero_poses.py has it.
    box(scene, 'Skiff left side', (.42, 0, middle), (.035, 1.5, gunwale_top - hull_bottom), wood)
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
    bpy.context.object.name = 'River water surface'
    bpy.context.object.data.materials.append(water)
    print(f'Water z=0 at the fingertips; floor z={floor_top:.3f}, seat z={seat_top:.3f}, hand x={hand_x:.3f}',
          flush=True)
    scene['water_z'] = 0.0
    if floor_top < .04:
        print(f'WARNING: the boat floor ({floor_top:.3f} m) is not above the water; lean her further', flush=True)
    camera = stage_camera(scene, 'Boat camera', (0, -4, .4), (0, 0, .4), 1.6)
    camera.data.type = 'PERSP'
    camera.data.lens = 50
    camera.location = (-.45, -2.9, floor_top + .55)
    aim = Vector((wall_x + .1, 0, floor_top + .22))
    camera.rotation_euler = (aim - camera.location).to_track_quat('-Z', 'Y').to_euler()
    light(scene, 'Key', (-1.4, -2.2, 2.4), (0, 0, .5), (1, .86, .72), 160, 1.6)
    light(scene, 'Fill', (1.8, -1.8, 1.2), (0, 0, .5), (.70, .82, 1), 50, 2.2)
    light(scene, 'Rim', (1.2, 1.8, 2.2), (0, 0, .6), (1, .78, .56), 160, 1.6)
    label(scene, 'Boat label', 'GOPAL\'S NIECE  •  HAND IN THE WATER', -.1, .02, .035, lettering, camera, -.2)
    render(scene, 'GopalNiece_In_Boat.png')


RENDERS = {'turnaround': turnaround, 'portrait': portrait, 'boat': boat_scene}


def main() -> None:
    args = shared.arguments()
    startup = bpy.context.scene
    character = make_character()
    if startup != character.scene:
        bpy.data.scenes.remove(startup)
    OUT.mkdir(parents=True, exist_ok=True)
    if '--no-save' not in args:
        export_fbx(character)
        bpy.context.window.scene = character.scene
        bpy.context.preferences.filepaths.save_version = 0
        if 'FINISHED' not in bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True):
            raise RuntimeError('Could not save the niece file')
    if '--renders' in args or '--only' in args:
        chosen = [args[args.index('--only') + 1]] if '--only' in args else list(RENDERS)
        for name in chosen:
            RENDERS[name](character)


if __name__ == '__main__':
    main()
