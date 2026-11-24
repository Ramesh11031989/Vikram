"""Build Nandu's daughter: editable .blend, FBX handoff and review renders.

    blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_nandu_daughter.py
    blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_nandu_daughter.py -- --renders

The first command writes Blender/Nandu_Daughter.blend and
Blender/Exports/CH_NanduDaughter.fbx; `--renders` also renders the previews in
Blender/Previews.  `--only NAME` renders a single preview while iterating.
"""

from __future__ import annotations

from collections.abc import Sequence
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cast import label, light, review_floor, setup_stage, stage_camera, studio_material
from child import ChildCharacter, Pose, add_child_facial_controls, apply_pose, reset_pose, save_pose_asset
import nandu_daughter
import reed_boat


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / 'Nandu_Daughter.blend'
FBX = ROOT / 'Exports' / 'CH_NanduDaughter.fbx'
PREVIEWS = ROOT / 'Previews'
CAST = ROOT / 'Vikram_Betal_Cast.blend'


def arguments() -> list[str]:
    return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def make_character() -> ChildCharacter:
    character = ChildCharacter(nandu_daughter.SPEC)
    character.body()
    character.face()
    nandu_daughter.dress(character)
    add_child_facial_controls(character)
    character.validate()
    rig = character.rig
    for pose in nandu_daughter.POSES:
        apply_pose(rig, pose)
        save_pose_asset(rig, pose, character.name)
    reset_pose(rig)
    print(f'{character.name}: {len(character.parts)} skinned meshes, {len(rig.data.bones)} bones, '
          f'{len(nandu_daughter.POSES)} pose assets', flush=True)
    return character


def palm_frame(rig, side: str) -> tuple[Vector, Vector, Vector]:
    """Posed palm socket in armature space: (centre, palm normal, finger direction)."""
    socket = rig.pose.bones[f'prop.{side}']
    rest_palm = socket.bone.matrix_local.to_3x3().inverted() @ Vector((0, 0, -1))
    rotation = socket.matrix.to_3x3().normalized()
    return socket.head.copy(), (rotation @ rest_palm).normalized(), rotation.col[1].normalized()


def boat_placement(rig, grip: str) -> Matrix:
    """Armature-space matrix for the boat (origin = hull bottom centre) for a grip.

    'right': lengthwise on the cupped right palm, bow along the fingers.
    'both': across both palms.  'above': being handed down onto both palms.
    """
    if grip == 'right':
        origin, up, fingers = palm_frame(rig, 'R')
        length = (fingers - up * up.dot(fingers)).normalized()
        origin = origin + length * .012
    else:
        right, up_r, _ = palm_frame(rig, 'R')
        left, up_l, _ = palm_frame(rig, 'L')
        origin, up = (right + left) / 2, (up_r + up_l).normalized()
        length = left - right
        length = (length - up * up.dot(length)).normalized()
        if grip == 'above':
            origin = origin + up * .07
    side = up.cross(length)
    matrix = Matrix((length, side, up)).transposed().to_4x4()
    matrix.translation = origin + up * .002
    return matrix


def attach_boat(collection, rig, grip: str) -> bpy.types.Object:
    """The shared reed boat, held by a Child Of constraint on the right palm socket."""
    boat = reed_boat.build(collection)
    hold = boat.constraints.new('CHILD_OF')
    hold.name = 'Daughter hand'
    hold.target = rig
    hold.subtarget = 'prop.R'
    hold.set_inverse_pending = False
    hold.inverse_matrix = Matrix.Identity(4)
    socket = rig.pose.bones['prop.R'].matrix
    boat.matrix_basis = socket.inverted() @ boat_placement(rig, grip)
    return boat


def export_fbx(character: ChildCharacter) -> None:
    bpy.context.window.scene = character.scene
    bpy.ops.object.select_all(action='DESELECT')
    character.rig.select_set(True)
    for part in character.parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = character.rig
    FBX.parent.mkdir(exist_ok=True)
    result = bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=False, add_leaf_bones=False,
        bake_anim=False, mesh_smooth_type='FACE', use_custom_props=True)
    if 'FINISHED' not in result or FBX.stat().st_size < 1024:
        raise RuntimeError(f'FBX export failed: {FBX}')


# ------------------------------------------------------------- review stage
def display_copy(scene, character: ChildCharacter, name: str, location: Sequence[float], yaw: float,
                 pose: Pose | None) -> bpy.types.Object:
    group = bpy.data.collections.new(f'{character.name} • {name}')
    scene.collection.children.link(group)
    rig = character.rig.copy()
    rig.name = f'{character.name} • {name} rig'
    rig.show_in_front = False
    group.objects.link(rig)
    for part in character.parts:
        clone = part.copy()
        group.objects.link(clone)
        clone.parent = rig
        clone.modifiers['Character Skinning'].object = rig
    rig.location = location
    rig.rotation_euler.z = math.radians(yaw)
    bpy.context.window.scene = scene
    if pose:
        apply_pose(rig, pose)
    return rig


def pose_named(name: str) -> Pose:
    return next(pose for pose in nandu_daughter.POSES if pose.name == name)


def render(scene, filename: str) -> None:
    bpy.context.window.scene = scene
    scene.render.filepath = str(PREVIEWS / filename)
    bpy.ops.render.render(write_still=True)
    print(f'Rendered {filename}', flush=True)


def turnaround(character: ChildCharacter) -> None:
    scene = bpy.data.scenes.new('Daughter • Turnaround')
    setup_stage(scene, 1600, 1000, 24, .2)
    review_floor((.045, .052, .058))
    lettering = studio_material('Labels • Warm sandstone', (.55, .47, .34))
    camera = stage_camera(scene, 'Turnaround camera', (0, -7, .62), (0, 0, .57), 2.6)
    light(scene, 'Key', (-2.4, -3.4, 3.6), (0, 0, .6), (1, .86, .72), 260, 2.0)
    light(scene, 'Fill', (2.4, -2.6, 1.8), (0, 0, .6), (.70, .82, 1), 70, 2.6)
    light(scene, 'Warm rim', (2.0, 2.4, 2.6), (0, 0, .75), (1, .78, .56), 240, 1.8)
    light(scene, 'Cool rim', (-2.2, 1.8, 2.2), (0, 0, .7), (.55, .72, 1), 120, 2.0)
    stand = pose_named('Stand')
    for index, (yaw, text) in enumerate(((0, 'FRONT'), (-35, 'THREE-QUARTER'), (-90, 'SIDE'), (180, 'BACK'))):
        x = -.93 + index * .62
        display_copy(scene, character, text.title(), (x, 0, 0), yaw, stand)
        label(scene, f'{text} label', text, x, .04, .042, lettering, camera, -.6)
    label(scene, 'Height label', "NANDU'S DAUGHTER  •  1.10 m  •  CHILD RIG", 0, 1.2, .045, lettering, camera, -.6)
    render(scene, 'NanduDaughter_Turnaround.png')


def portrait(character: ChildCharacter) -> None:
    """Face study: front, three-quarter and profile close-ups at the same scale."""
    scene = bpy.data.scenes.new('Daughter • Portrait')
    setup_stage(scene, 1800, 820, 40, .16)
    review_floor((.03, .036, .042))
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 1.2, 1), rotation=(math.radians(90), 0, 0))
    bpy.context.object.name = 'Portrait backdrop'
    bpy.context.object.data.materials.append(studio_material('Backdrop • Charcoal', (.035, .04, .047)))
    stand = pose_named('Stand')
    eye = character.rig.data.bones['eye.L'].head_local
    z = eye.z - .03
    camera = stage_camera(scene, 'Portrait camera', (0, -4, z), (0, 0, z), .62)
    camera.data.type = 'PERSP'
    camera.data.lens = 135
    camera.location = (0, -2.55, z + .015)
    light(scene, 'Portrait key', (-1.1, -1.5, z + 1.0), (0, 0, z), (1, .85, .72), 80, .9)
    light(scene, 'Portrait fill', (1.3, -1.3, z + .3), (0, 0, z), (.68, .8, 1), 28, 1.3)
    light(scene, 'Hair rim', (.9, 1.2, z + .8), (0, 0, z + .05), (1, .8, .6), 70, .8)
    light(scene, 'Cool rim', (-1.0, .9, z + .5), (0, 0, z), (.6, .75, 1), 40, .8)
    for x, yaw, name in ((-.225, 0, 'front'), (0, -38, 'three-quarter'), (.215, -90, 'profile')):
        display_copy(scene, character, f'Portrait {name}', (x, 0, 0), yaw, stand)
    render(scene, 'NanduDaughter_Portrait.png')


def hand_poses(character: ChildCharacter) -> None:
    scene = bpy.data.scenes.new('Daughter • Boat hand poses')
    setup_stage(scene, 1800, 1000, 20, .2)
    review_floor((.045, .052, .058))
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 1.6, 1), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(studio_material('Backdrop • Charcoal', (.035, .04, .047)))
    lettering = studio_material('Labels • Warm sandstone', (.55, .47, .34))
    camera = stage_camera(scene, 'Hands camera', (0, -4, .8), (0, 0, .75), 1.0)
    camera.data.type = 'PERSP'
    camera.data.lens = 50
    camera.location = (.3, -3.3, 1.02)
    target = Vector((.05, 0, .50))
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    light(scene, 'Key', (-1.6, -2.4, 2.4), (0, 0, .8), (1, .86, .72), 160, 1.6)
    light(scene, 'Fill', (2.0, -2.0, 1.2), (0, 0, .8), (.70, .82, 1), 50, 2.2)
    light(scene, 'Rim', (1.2, 1.8, 2.2), (0, 0, .9), (1, .78, .56), 160, 1.6)
    for x, (name, grip) in zip((-.66, .04, .74), (('Carry boat', 'right'), ('Offer boat', 'both'),
                                                  ('Reach to take back', 'above'))):
        rig = display_copy(scene, character, name, (x, 0, 0), -40, pose_named(name))
        attach_boat(rig.users_collection[0], rig, grip)
        label(scene, f'{name} label', name.upper(), x, .03, .036, lettering, camera, -.45)
    render(scene, 'NanduDaughter_Boat_Hands.png')


def adult(scene, name: str, location: Sequence[float], yaw: float) -> bpy.types.Object:
    """An instance of a posed adult from the cast library (linked, never copied into this file)."""
    label_name = f'{name} • Display pose'
    group = next((c for c in bpy.data.collections if c.name == label_name and c.library), None)
    if group is None:
        with bpy.data.libraries.load(str(CAST), link=True) as (_, target):
            target.collections = [label_name]
        group = target.collections[0]
    instance = bpy.data.objects.new(f'{name} in the crowd', None)
    instance.instance_type = 'COLLECTION'
    instance.instance_collection = group
    scene.collection.objects.link(instance)
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()  # evaluates the linked objects' world matrices
    corners = [o.matrix_world @ Vector(corner) for o in group.all_objects if o.type == 'MESH'
               for corner in o.bound_box]
    footprint = Vector(((min(p.x for p in corners) + max(p.x for p in corners)) / 2,
                        (min(p.y for p in corners) + max(p.y for p in corners)) / 2, 0))
    instance.matrix_world = (Matrix.Translation(Vector(location)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
                             @ Matrix.Translation(-footprint))
    return instance


def crowd(character: ChildCharacter) -> None:
    """Height check: she slips between the adults of a crowd, her head at their waists."""
    scene = bpy.data.scenes.new('Daughter • Crowd height')
    setup_stage(scene, 1800, 1000, 20, .2)
    review_floor((.045, .052, .058))
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 2.4, 2), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(studio_material('Backdrop • Charcoal', (.035, .04, .047)))
    lettering = studio_material('Labels • Warm sandstone', (.55, .47, .34))
    camera = stage_camera(scene, 'Crowd camera', (0, -5, 1), (0, 0, .9), 4)
    camera.data.type = 'PERSP'
    camera.data.lens = 42
    camera.location = (.45, -5.2, 1.05)
    target = Vector((.05, 0, .86))
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    light(scene, 'Key', (-2.4, -3.4, 3.6), (0, 0, .9), (1, .86, .72), 420, 2.4)
    light(scene, 'Fill', (2.6, -2.8, 1.8), (0, 0, .9), (.70, .82, 1), 110, 2.8)
    light(scene, 'Rim', (1.8, 2.2, 3.0), (0, 0, 1.2), (1, .78, .56), 300, 2.0)
    for name, location, yaw in (('Vikram', (-1.25, .45, 0), 12), ('Gopal', (-.40, .06, 0), 8),
                                ('Gopal', (.38, .12, 0), -9), ('Gopal', (1.22, .50, 0), -18)):
        adult(scene, name, location, yaw)
    display_copy(scene, character, 'In the crowd', (-.01, -.16, 0), -28, pose_named('Stand'))
    label(scene, 'Crowd label', "NANDU'S DAUGHTER  •  1.10 m  •  HEAD AT AN ADULT'S WAIST", .05, .06, .05,
          lettering, camera, -.9)
    render(scene, 'NanduDaughter_Crowd_Height.png')


RENDERS = {'turnaround': turnaround, 'portrait': portrait, 'hands': hand_poses, 'crowd': crowd}


def main() -> None:
    args = arguments()
    startup = bpy.context.scene
    character = make_character()
    if startup != character.scene:  # drop the factory cube scene
        bpy.data.scenes.remove(startup)
    if '--no-save' not in args:
        export_fbx(character)
        bpy.context.window.scene = character.scene
        bpy.context.preferences.filepaths.save_version = 0
        result = bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
        if 'FINISHED' not in result:
            raise RuntimeError('Could not save the daughter library file')
    if '--renders' in args or '--only' in args:
        PREVIEWS.mkdir(exist_ok=True)
        chosen = [args[args.index('--only') + 1]] if '--only' in args else list(RENDERS)
        for name in chosen:
            RENDERS[name](character)


if __name__ == '__main__':
    main()
