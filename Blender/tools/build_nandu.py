"""Build Nandu (गेट keeper) into Blender/Nandu.blend, export FBX and render review images.

blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_nandu.py
Add `-- --no-video` to skip the two turntable/test-shot videos.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import shutil
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cast as stage
from character import Character
import facial_controls as face
import nandu_body as body
import nandu_groom as hair
import gopal
import nandu
import nandu_rig as kit
import proportions
from textile import apply_textiles


ROOT = Path(__file__).resolve().parents[1]
PREVIEWS = ROOT/'Previews'
EXPORTS = ROOT/'Exports'
FRAMES = Path(bpy.app.tempdir or '/tmp')/'nandu_frames'
DAUGHTER_HEIGHT = 1.10  # From the daughter thread's plan; her model replaces the placeholder.
VIDEO = '--no-video' not in sys.argv


def build_nandu() -> tuple[Character, object, object]:
    c = body.NanduCharacter(nandu.SPEC)
    body.body(c)                  # shared legs, realistic arms, sculpted 20-joint hands
    body.face(c)                  # sculpted head, eyes, ears, brows, mouth
    nandu.dress(c)
    hair.groom(c)
    apply_textiles(c)
    face.add_facial_controls(c)
    body.finish_face(c)           # sculpted blinks, teeth, tongue and speech shapes
    kit.add_wrist_rig(c)
    kit.wrist_rope(c, c.mat('Jute rope', (.28, .21, .11), .96))
    kit.add_expressions(c)
    c.validate()
    cloth = kit.red_cloth(c)
    boat = kit.reed_boat(c)
    kit.grip_library(c)
    c.scene.name = 'Library | Nandu'
    print(f'Nandu: {len(c.parts)} skinned meshes, {len(c.rig.data.bones)} bones', flush=True)
    return c, cloth, boat


# ---------------------------------------------------------------- scene helpers

def clone(c, cloth, scene, label: str):
    """Independent copy of the rig and meshes, with drivers and constraints pointing at the copy."""
    group = bpy.data.collections.new(f'Nandu • {label}')
    scene.collection.children.link(group)
    rig = c.rig.copy()
    rig.name = f'Nandu • {label} rig'
    rig.show_in_front = False
    group.objects.link(rig)
    for bone in rig.pose.bones:
        for constraint in bone.constraints:
            for attr in ('target', 'pole_target'):
                if getattr(constraint, attr, None) == c.rig:
                    setattr(constraint, attr, rig)
    _retarget(rig, c.rig, rig)
    parts = []
    for part in c.parts:
        copy = part.copy()
        group.objects.link(copy)
        copy.parent = rig
        copy.modifiers['Character Skinning'].object = rig
        _retarget(copy, c.rig, rig)
        parts.append(copy)
    gamchha = cloth.copy()
    gamchha.name = f'Nandu • {label} gamchha'
    group.objects.link(gamchha)
    _retarget(gamchha, cloth, gamchha)
    kit.bind_red_cloth(gamchha, rig)
    return rig, parts, gamchha


def _retarget(obj, old, new) -> None:
    if obj.animation_data:
        for curve in obj.animation_data.drivers:
            for variable in curve.driver.variables:
                for target in variable.targets:
                    if target.id == old:
                        target.id = new


def relax_arms(rig) -> None:
    for side, sign in (('L', 1), ('R', -1)):
        stage.turn(rig, f'upper_arm.{side}', (0, 1, 0), sign*76)
        stage.turn(rig, f'forearm.{side}', (0, 0, 1), sign*-12)
    kit.apply_grip(rig, 'Return toy boat')


def studio(name: str, width: int, height: int, samples: int, floor=(.041, .055, .061)):
    scene = bpy.data.scenes.new(name)
    stage.setup_stage(scene, width, height, samples, .22)
    stage.review_floor(floor)
    return scene


def key_lights(scene, scale: float = 1.0) -> None:
    stage.light(scene, 'Angled daylight', (-2.9, -3.9, 5.3), (0, 0, 1.1), (1, .84, .70), 490*scale, 2.2)
    stage.light(scene, 'Cool fill', (2.3, -2.4, 3.1), (0, 0, 1), (.70, .82, 1), 132*scale, 3.2)
    stage.light(scene, 'Warm rim', (2.3, 2.6, 4.3), (0, 0, 1.25), (1, .77, .54), 480*scale, 2.1)
    stage.light(scene, 'Blue rim', (-2.4, 1.1, 2.8), (0, 0, 1.05), (.53, .71, 1), 180*scale, 2.3)


def render(scene, path: Path, frame: int | None = None) -> Path:
    bpy.context.window.scene = scene
    if frame is not None:
        scene.frame_set(frame)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def ffmpeg(*args: str) -> None:
    if not shutil.which('ffmpeg'):
        raise RuntimeError('ffmpeg is needed to assemble the review sheets')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *args], check=True)


# ---------------------------------------------------------------- review scenes

def turntable(c, cloth):
    scene = studio('Nandu • Turntable', 720, 900, 16)
    rig, _, _ = clone(c, cloth, scene, 'Turntable')
    relax_arms(rig)
    camera = stage.stage_camera(scene, 'Turntable camera', (0, -7, 1.02), (0, 0, .86), 2.05)
    pivot = bpy.data.objects.new('Turntable pivot', None)
    scene.collection.objects.link(pivot)
    camera.parent = pivot
    key_lights(scene)
    scene.frame_start, scene.frame_end = 1, 48
    preferences = bpy.context.preferences.edit
    previous = preferences.keyframe_new_interpolation_type
    preferences.keyframe_new_interpolation_type = 'LINEAR'
    for frame, angle in ((1, 0), (49, 360)):
        pivot.rotation_euler.z = math.radians(angle)
        pivot.keyframe_insert('rotation_euler', index=2, frame=frame)
    preferences.keyframe_new_interpolation_type = previous
    return scene


def tied_test(c, cloth, boat):
    scene = studio('Nandu • Tied hands reach test', 1280, 720, 20, (.075, .066, .055))
    rig, _, _ = clone(c, cloth, scene, 'Tied test')
    rig[kit.TIED] = 1.0
    toy = boat.copy()
    toy.constraints.clear()
    scene.collection.objects.link(toy)
    # Placeholder daughter: palm held out at her chest height. GUESS until she is modeled.
    skin = stage.studio_material('Stand-in | child placeholder', (.30, .25, .22), .8)
    palm = (0, -.60, .98)
    bpy.ops.mesh.primitive_cylinder_add(radius=.11, depth=DAUGHTER_HEIGHT*.8, location=(0, -.92, DAUGHTER_HEIGHT*.4))
    stage.prop_material(bpy.context.object, skin).name = 'Daughter placeholder body'
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.09, location=(0, -.92, DAUGHTER_HEIGHT-.09))
    stage.prop_material(bpy.context.object, skin).name = 'Daughter placeholder head'
    bpy.ops.mesh.primitive_cylinder_add(radius=.025, depth=.30, location=(0, -.74, .93), rotation=(math.pi/2-.45, 0, 0))
    stage.prop_material(bpy.context.object, skin).name = 'Daughter placeholder forearm'
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=palm)
    hand = bpy.context.object
    hand.scale = (kit.CHILD_PALM_WIDTH/2, kit.CHILD_HAND_LENGTH*.3, .009)
    stage.prop_material(hand, skin).name = 'Daughter placeholder palm'
    toy.location = (palm[0], palm[1], palm[2]+.008)
    toy.rotation_euler.z = 0  # across her palm
    toy.scale = (1, 1, 1)

    camera = stage.stage_camera(scene, 'Test shot camera', (2.3, -2.6, 1.45), (0, -.42, 1.0), 1.5)
    camera.data.type = 'PERSP'
    camera.data.lens = 42
    stage.aim(camera, (.02, -.40, 1.0))
    key_lights(scene, .8)
    scene.frame_start, scene.frame_end = 1, 48
    # Targets stay inside the arms' reach (about 44 cm from the shoulder) so the bound wrists
    # stay together; the lean does the rest. The child's palm sits just beyond his fingertips.
    # Each target is placed from the leaning shoulders, inside the arms' 44 cm reach,
    # so the bound wrists stay together; the lean carries the hands toward the boat.
    keys = ((1, 0, None, 'Hold'), (18, 12, (-.20, -.26), 'Hold'),
            (34, 30, (-.36, -.28), 'Reach'), (48, 34, (-.40, -.30), 'Reach'))
    for frame, lean, offset, grip in keys:
        scene.frame_set(frame)
        stage.turn(rig, 'spine', (1, 0, 0), lean*.45)
        stage.turn(rig, 'chest', (1, 0, 0), lean*.55)
        stage.turn(rig, 'head', (1, 0, 0), -lean*.2)
        kit.apply_grip(rig, grip)
        for bone in ('spine', 'chest', 'head', *kit.HAND_BONES):
            rig.pose.bones[bone].keyframe_insert('rotation_quaternion', frame=frame)
        bpy.context.view_layer.update()
        bind = rig.pose.bones['wrist_bind']
        if offset is None:
            bind.location = (0, 0, 0)
            bind.rotation_quaternion = (1, 0, 0, 0)
            bind.keyframe_insert('location', frame=frame)
            bind.keyframe_insert('rotation_quaternion', frame=frame)
            continue
        shoulders = [rig.matrix_world @ rig.pose.bones[f'upper_arm.{side}'].head for side in 'LR']
        middle = (shoulders[0]+shoulders[1])/2
        target = middle + Vector((0, offset[0], offset[1]))*c.scale
        rest = bind.bone.matrix_local.copy()
        world = Matrix.Translation(target) @ rest.to_3x3().to_4x4()
        bind.matrix = rig.matrix_world.inverted() @ world
        bind.keyframe_insert('location', frame=frame)
        bind.keyframe_insert('rotation_quaternion', frame=frame)
    scene.frame_set(1)
    return scene


def chauki_test(cloth):
    """Red gamchha re-targeted to an anonymous rig: back and shoulder only, as Gopal sees it."""
    scene = studio('Nandu • Chauki red cloth on anonymous rig', 1280, 720, 24, (.03, .03, .035))
    spec = dict(name='ChaukiFigure', height=nandu.SPEC['height'], skin=(.07, .05, .035), hair=(.02, .016, .013),
                iris=(.05, .03, .02), face_width=1.0, nose_width=1.0, brow_lift=0)
    figure = Character(spec)
    figure.body()
    figure.face()
    dark = figure.mat('Unlit shawl', (.05, .045, .04), .95)
    figure.loft('Dark wrap', [(.60, 0, .004, .23, .16), (.98, 0, .004, .17, .115), (1.2, 0, .005, .185, .115),
                              (1.36, 0, .003, .205, .09), (1.42, 0, .008, .06, .05)], dark, 'chest')
    figure.ovoid('Covered head', (0, .01, 1.70), (.125, .125, .13), dark, 'head')
    proportions.realistic_head(figure)
    scene.collection.children.link(figure.collection)
    bpy.context.window.scene = scene
    # Back three-quarters to Gopal's boat: only the back and the cloth on the shoulder read.
    figure.rig.rotation_euler.z = math.radians(-28)
    figure.rig.location = (0, 0, .35)
    for side, sign in (('L', 1), ('R', -1)):
        stage.turn(figure.rig, f'upper_arm.{side}', (0, 1, 0), sign*74)
        stage.turn(figure.rig, f'forearm.{side}', (0, 0, 1), sign*-20)
    gamchha = cloth.copy()
    gamchha.name = 'Red gamchha • on anonymous rig'
    scene.collection.objects.link(gamchha)
    _retarget(gamchha, cloth, gamchha)
    kit.bind_red_cloth(gamchha, figure.rig)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, .1, .17))
    stage.prop_material(bpy.context.object, stage.studio_material('Chauki | wet stone', (.06, .055, .05))).name = 'Chauki platform'
    bpy.context.object.scale = (1.2, 1.0, .34)
    lamp = bpy.data.lights.new('Chauki diya', 'POINT')
    lamp.energy, lamp.color, lamp.shadow_soft_size = 12, (1, .58, .25), .03
    diya = bpy.data.objects.new('Chauki diya', lamp)
    scene.collection.objects.link(diya)
    diya.location = (.42, .42, 1.30)
    camera = stage.stage_camera(scene, 'Gopal eye-line', (-1.9, 4.6, 1.62), (0, 0, 1.55), 1)
    camera.data.type = 'PERSP'
    camera.data.lens = 70
    stage.aim(camera, (0, .02, 1.62))
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .02
    return scene


def lineup(c, cloth, boat):
    scene = studio('Nandu • Scale lineup', 1440, 1050, 24)
    camera = stage.stage_camera(scene, 'Lineup camera', (0, -7, 2.0), (0, 0, .93), 3.0)
    key_lights(scene)
    lettering = stage.studio_material('Labels • Warm sandstone', (.55, .47, .34))
    gopal_character = stage.make_character(gopal)
    bpy.context.window.scene = scene
    gopal_rig = stage.showcase_character(scene, gopal_character, -.95, 9)
    rig, _, _ = clone(c, cloth, scene, 'Lineup')
    relax_arms(rig)
    rig.location.x = .12
    skin = stage.studio_material('Stand-in | child placeholder', (.30, .25, .22), .8)
    bpy.ops.mesh.primitive_cylinder_add(radius=.11, depth=DAUGHTER_HEIGHT*.82, location=(1.02, 0, DAUGHTER_HEIGHT*.41))
    stage.prop_material(bpy.context.object, skin)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.09, location=(1.02, 0, DAUGHTER_HEIGHT-.09))
    stage.prop_material(bpy.context.object, skin)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(1.02, -.16, .78))
    palm = bpy.context.object
    palm.scale = (kit.CHILD_PALM_WIDTH/2, kit.CHILD_HAND_LENGTH*.3, .009)
    stage.prop_material(palm, skin)
    toy = boat.copy()
    toy.constraints.clear()
    scene.collection.objects.link(toy)
    toy.location = (1.02, -.16, .788)
    toy.rotation_euler.z = 0
    for name, x in (('GOPAL  181 cm', -.95), ('NANDU  170 cm', .12), ('BETI  placeholder 110 cm', 1.02)):
        stage.label(scene, f'{name} label', name, x, .034, .062, lettering, camera, -.85)
    for z in (1.0, 1.5):
        bpy.ops.mesh.primitive_cylinder_add(radius=.0016, depth=3.2, location=(.05, .6, z), rotation=(0, math.pi/2, 0))
        stage.prop_material(bpy.context.object, lettering)
    return scene


def expressions_sheet(c) -> Path:
    scene = c.scene
    stage.setup_stage(scene, 640, 720, 24, .18)
    stage.review_floor((.027, .039, .048))
    face_z = c.sculpted.final((0, 0, 1.42)).z
    camera = stage.stage_camera(scene, 'Portrait camera', (-.9, -4.7, face_z-.02), (0, 0, face_z), .32)
    stage.light(scene, 'Portrait key', (-1.7, -2.0, 3.3), (0, 0, 1.53), (1, .84, .71), 168, 1.45)
    stage.light(scene, 'Portrait fill', (1.8, -2.2, 2.2), (0, 0, 1.54), (.65, .79, 1), 68, 2.0)
    stage.light(scene, 'Hair rim', (1.2, 1.8, 2.6), (0, 0, 1.62), (1, .78, .56), 195, 1.45)
    tiles = []
    for name in ('neutral', *kit.EXPRESSIONS):
        for prop in kit.EXPRESSIONS:
            c.rig[prop] = 1.0 if prop == name else 0.0
        c.rig.update_tag()
        tiles.append(render(scene, FRAMES/f'expression_{name}.png', 1))
    for prop in kit.EXPRESSIONS:
        c.rig[prop] = 0.0
    out = PREVIEWS/'Nandu_Expressions.png'
    inputs = [arg for tile in tiles for arg in ('-i', str(tile))]
    ffmpeg(*inputs, '-filter_complex', f'hstack={len(tiles)}', str(out))
    for obj in list(scene.objects):
        if obj.type in ('LIGHT', 'CAMERA') or obj.name.startswith('Studio floor'):
            bpy.data.objects.remove(obj, do_unlink=True)
    return out


def checks(c, cloth, boat) -> dict:
    bpy.context.window.scene = c.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    tops = [max((part.matrix_world @ v.co).z for v in part.evaluated_get(depsgraph).data.vertices)
            for part in c.parts if part.name.endswith('_Head')]
    hand = next(p for p in c.parts if p.name.endswith('_Hand.R'))
    xs = [v.co.x for v in hand.data.vertices]
    ys = [v.co.y for v in hand.data.vertices]
    boat_dims = boat.dimensions
    report = {
        'character': 'Nandu', 'rig_bones': len(c.rig.data.bones), 'shared_bones_with_Gopal': 34,
        'skinned_meshes': len(c.parts), 'head_top_cm': round(max(tops)*100, 1),
        'face': 'sculpted_face.SculptedFace with nandu_body.NANDU_FACE',
        'hand_length_cm': round((max(xs)-min(xs))*100, 1),
        'gopal_head_top_cm': round(1.812*gopal.SPEC['height']*100, 1),
        'daughter_height_cm_placeholder': DAUGHTER_HEIGHT*100,
        'boat_length_cm': round(boat_dims.x*100, 1), 'boat_beam_cm': round(boat_dims.y*100, 1),
        'boat_height_cm': round(boat_dims.z*100, 1),
        'child_palm_width_cm': kit.CHILD_PALM_WIDTH*100, 'child_hand_length_cm': kit.CHILD_HAND_LENGTH*100,
        'nandu_hand_width_cm': round((max(ys)-min(ys))*100, 1),
        'head_shapes': list(bpy.data.objects['Nandu_Head'].data.shape_keys.key_blocks.keys()),
        'grip_poses': list(kit.GRIPS), 'expressions': list(kit.EXPRESSIONS),
        'red_cloth': {'object': cloth.name, 'constraint': 'Child Of → chest, influence from "attached"',
                      'cloth_modifier': 'Gamchha cotton (disabled until baked per shot)'},
    }
    # Lies across her palm: longer than the palm is wide, shorter than her whole hand plus a margin.
    report['boat_fits_child_palm'] = report['child_palm_width_cm'] < report['boat_length_cm'] <= report['child_hand_length_cm'] + 3
    report['boat_fits_nandu_grip'] = report['boat_length_cm'] <= report['hand_length_cm']
    return report


def export(c, cloth, boat) -> Path:
    bpy.context.window.scene = c.scene
    bpy.ops.object.select_all(action='DESELECT')
    for obj in (c.rig, *c.parts, cloth, boat):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = c.rig
    target = EXPORTS/'CH_Nandu.fbx'
    result = bpy.ops.export_scene.fbx(filepath=str(target), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=False, add_leaf_bones=False,
        bake_anim=False, mesh_smooth_type='FACE', use_custom_props=True)
    if 'FINISHED' not in result or target.stat().st_size < 1024:
        raise RuntimeError('Nandu FBX export failed')
    return target


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(exist_ok=True)
    EXPORTS.mkdir(exist_ok=True)
    default = bpy.context.scene
    c, cloth, boat = build_nandu()
    bpy.data.scenes.remove(default)
    report = checks(c, cloth, boat)
    fbx = export(c, cloth, boat)
    report['fbx'] = fbx.name
    sheet = expressions_sheet(c)
    table = turntable(c, cloth)
    test = tied_test(c, cloth, boat)
    chauki = chauki_test(cloth)
    bpy.context.window.scene = table
    bpy.context.preferences.filepaths.save_version = 0
    result = bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Nandu.blend'), compress=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Could not save Nandu.blend')

    for index, frame in enumerate((1, 7, 13, 19, 25, 31, 37, 43)):
        render(table, FRAMES/f'turn_{index}.png', frame)
    ffmpeg(*[a for i in range(8) for a in ('-i', str(FRAMES/f'turn_{i}.png'))],
           '-filter_complex', 'hstack=8,scale=2880:-1', str(PREVIEWS/'Nandu_Turntable_Sheet.png'))
    render(test, PREVIEWS/'Nandu_Tied_Hands_Test.png', 46)
    render(test, FRAMES/'tied_rest.png', 1)
    render(chauki, PREVIEWS/'Nandu_Chauki_RedCloth_Test.png', 1)
    if VIDEO:
        for scene, name, size in ((table, 'Nandu_Turntable.mp4', (480, 600)), (test, 'Nandu_Tied_Hands_Test.mp4', (960, 540))):
            scene.render.resolution_x, scene.render.resolution_y = size
            scene.cycles.samples = 10
            for frame in range(scene.frame_start, scene.frame_end+1):
                render(scene, FRAMES/f'{name[:-4]}_{frame:03d}.png', frame)
            ffmpeg('-framerate', '24', '-i', str(FRAMES/f'{name[:-4]}_%03d.png'), '-c:v', 'libx264',
                   '-pix_fmt', 'yuv420p', '-crf', '22', str(PREVIEWS/name))
    # Built last and not saved: Gopal for the scale lineup only.
    render(lineup(c, cloth, boat), PREVIEWS/'Nandu_Lineup.png', 1)
    report['previews'] = sorted(p.name for p in PREVIEWS.glob('Nandu_*'))
    (EXPORTS/'CH_Nandu_Check.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print('NANDU_BUILD_COMPLETE', json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
