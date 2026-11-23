"""Build the chapter cast, an editable character library and its FBX handoff."""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character import Character
from cloth_motion import attach_motion, bake_and_verify
from groom import groom
from textile import apply_textiles, store_rest_positions
import betal
import gopal
import vikram


ROOT = Path(__file__).resolve().parents[1]


def select_rig(character):
    bpy.context.window.scene = character.scene
    bpy.ops.object.select_all(action='DESELECT')
    character.rig.select_set(True)
    bpy.context.view_layer.objects.active = character.rig


def make_character(module):
    character = Character(module.SPEC)
    character.body()
    character.face()
    module.dress(character)
    groom(character)
    apply_textiles(character)
    character.validate()
    select_rig(character)
    print(f'{character.name}: {len(character.parts)} skinned meshes, '
          f'{len(character.rig.data.bones)} bones, 5 phoneme shapes', flush=True)
    return character


def export_fbx(character):
    select_rig(character)
    for part in character.parts:
        part.select_set(True)
    filepath = ROOT / 'Exports' / f'CH_{character.name}.fbx'
    result = bpy.ops.export_scene.fbx(filepath=str(filepath), use_selection=True,
        object_types={'ARMATURE','MESH'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=False,
        add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE')
    if 'FINISHED' not in result or filepath.stat().st_size < 1024:
        raise RuntimeError(f'FBX export failed: {filepath}')
    select_rig(character)


def studio_material(name, rgb, roughness=.82, metal=0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*rgb,1)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb,1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metal
    return material


def prop_material(obj, mat):
    obj.data.materials.append(mat)
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def light(scene, name, location, target, color, energy, size):
    data = bpy.data.lights.new(name,'AREA')
    data.color, data.energy, data.shape, data.size = color, energy, 'DISK', size
    obj = bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location = location
    aim(obj,target)


def turn(rig, joint, axis, degrees):
    bone = rig.pose.bones[joint]
    rest = bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = rest.inverted() @ Quaternion(axis, math.radians(degrees)) @ rest


def showcase_character(scene, character, x, yaw):
    display = bpy.data.collections.new(f'{character.name} • Display pose')
    scene.collection.children.link(display)
    rig = character.rig.copy()
    rig.name = f'{character.name} • Display rig'
    rig.show_in_front = False
    display.objects.link(rig)
    for part in character.parts:
        clone = part.copy()
        display.objects.link(clone)
        clone.parent = rig
        clone.modifiers['Character Skinning'].object = rig
    rig.location.x = x
    rig.rotation_euler.z = math.radians(yaw)
    gestures = {'Vikram': ((78,-7),(77,-31)), 'Betal': ((79,-19),(82,-7)),
                'Gopal': ((79,-9),(72,-54))}
    for (side, sign), (arm_angle, elbow_angle) in zip((('L',1),('R',-1)), gestures[character.name]):
        turn(rig, f'upper_arm.{side}', (0,1,0), sign*arm_angle)
        turn(rig, f'forearm.{side}', (0,0,1), sign*elbow_angle)
        for digit in range(1,5):
            turn(rig, f'finger_{digit:02d}.{side}', (0,1,0), sign*(16+digit*3))
    turn(rig, 'head', (0,0,1), {'Vikram':-3,'Betal':7,'Gopal':-8}[character.name]-yaw*.35)
    turn(rig, 'neck', (1,0,0), {'Vikram':-2,'Betal':4,'Gopal':-3}[character.name])
    turn(rig, 'chest', (0,1,0), {'Vikram':-1,'Betal':-4,'Gopal':3}[character.name])
    return rig


def label(scene, name, value, x, z, size, material, camera, y=-.07):
    text = bpy.data.curves.new(name,'FONT')
    text.body, text.size, text.align_x, text.align_y = value, size, 'CENTER', 'CENTER'
    text.space_character = 1.21
    obj = bpy.data.objects.new(name,text)
    scene.collection.objects.link(obj)
    obj.location = (x,y,z)
    obj.rotation_euler = camera.rotation_euler
    prop_material(obj,material)


def configure_view(scene, camera=False):
    bpy.context.window.scene = scene
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            view = area.spaces.active
            view.shading.color_type = 'MATERIAL'
            view.shading.light = 'STUDIO'
            view.shading.show_shadows = True
            view.overlay.show_overlays = not camera
            view.region_3d.view_location = (0,0,1)
            view.region_3d.view_distance = 4.0
            view.region_3d.view_rotation = Quaternion((1,0,0), math.radians(84))
            view.region_3d.view_perspective = 'CAMERA' if camera else 'ORTHO'


def setup_stage(scene, width, height, samples, world_strength):
    bpy.context.window.scene = scene
    scene.render.fps = 24
    scene.unit_settings.system = 'METRIC'
    scene.world = bpy.data.worlds.new(f'{scene.name} • Ambient')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.28,.35,.45,1)
    background.inputs['Strength'].default_value = world_strength
    scene.view_settings.view_transform = 'AgX'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.adaptive_threshold = .035
    scene.cycles.use_denoising = True
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'

def stage_camera(scene, name, location, target, width):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = width
    camera = bpy.data.objects.new(name,cam_data)
    scene.collection.objects.link(camera)
    camera.location = location
    aim(camera,target)
    scene.camera = camera
    return camera


def review_floor(color):
    bpy.ops.mesh.primitive_plane_add(size=100, location=(0,0,-.008))
    floor = prop_material(bpy.context.object, studio_material('Backdrop • Slate',color))
    floor.name = 'Studio floor'


def studio(scene, cast):
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.name = 'Cast Preview'
    setup_stage(scene, 1440, 1050, 24, .22)
    review_floor((.041,.055,.061))
    lettering = studio_material('Labels • Warm sandstone',(.55,.47,.34))
    camera = stage_camera(scene, 'Cast camera', (0,-7,2.07), (0,0,.955), 3.43)
    light(scene, 'Angled daylight', (-2.9,-3.9,5.3), (0,0,1.1), (1,.84,.70), 490,2.2)
    light(scene, 'Cool fill', (2.3,-2.4,3.1), (0,0,1), (.70,.82,1), 132,3.2)
    light(scene, 'Warm rim', (2.3,2.6,4.3), (0,0,1.25), (1,.77,.54), 480,2.1)
    light(scene, 'Blue rim', (-2.4,1.1,2.8), (0,0,1.05), (.53,.71,1), 180,2.3)
    for character, x, yaw in zip(cast,(-1.04,0,1.04),(13,-7,9)):
        showcase_character(scene,character,x,yaw)
        label(scene, f'{character.name} Label', character.name.upper(), x, .034, .073, lettering, camera, -.85)
    bpy.ops.object.select_all(action='DESELECT')
    scene.render.filepath = '//Previews/Cast_Lineup.png'


def surface_review(cast):
    scene = bpy.data.scenes.new('Surface Detail')
    setup_stage(scene, 1600, 735, 32, .18)
    review_floor((.027,.039,.048))
    stage_camera(scene, 'Portrait camera', (0,-5,1.83), (0,0,1.57), 1.85)
    light(scene, 'Portrait key', (-1.7,-2.0,3.3), (0,0,1.53), (1,.84,.71), 168,1.45)
    light(scene, 'Portrait fill', (1.8,-2.2,2.2), (0,0,1.54), (.65,.79,1), 68,2.0)
    light(scene, 'Gold hair rim', (1.2,1.8,2.6), (0,0,1.62), (1,.78,.56), 195,1.45)
    light(scene, 'Cool hair rim', (-1.6,1.0,2.4), (0,0,1.62), (.63,.80,1), 130,1.45)
    for character, x, yaw, z in zip(cast,(-.61,0,.61),(15,0,-10),(-.12,.048,-.018)):
        rig = showcase_character(scene,character,x,yaw)
        rig.location.z = z
    scene.render.filepath = '//Previews/Cast_Detail.png'
    return scene


def wind_review(character):
    scene = bpy.data.scenes.new('Betal • Cloth Wind Test')
    setup_stage(scene, 720, 480, 16, .24)
    review_floor((.092,.083,.073))
    stage_camera(scene, 'Sash camera', (1.65,-4,1.34), (.19,-.08,.82), 1.30)
    light(scene, 'Sash key', (-2,-3,3.8), (0,0,.85), (1,.87,.71), 350,2.1)
    light(scene, 'Sash fill', (2.5,-1.4,2.2), (0,0,.86), (.64,.79,1), 109,1.95)
    light(scene, 'Sash rim', (1.5,1.8,3.4), (0,0,.85), (1,.76,.56), 275,1.9)
    rig = showcase_character(scene, character, 0, 0)
    cloth = attach_motion(scene, character, rig)
    store_rest_positions(cloth.data)
    return scene, cloth


def render_still(scene):
    bpy.context.window.scene = scene
    bpy.ops.render.render(write_still=True)


def render_wind_video():
    scene = bpy.data.scenes['Betal • Cloth Wind Test']
    bpy.context.window.scene = scene
    scene.frame_set(scene.frame_start)
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = 624
    scene.render.resolution_y = 416
    scene.render.image_settings.media_type = 'VIDEO'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    target = ROOT/'Previews'/'Betal_Cloth_Wind.mp4'
    scene.render.filepath = str(target)
    scene.render.use_file_extension = False
    bpy.ops.render.render(animation=True)
    if not target.is_file() or target.stat().st_size < 1024:
        raise RuntimeError(f'Could not render cloth review video: {target}')


def main():
    (ROOT/'Exports').mkdir(exist_ok=True)
    (ROOT/'Previews').mkdir(exist_ok=True)
    preview = bpy.context.scene
    cast = [make_character(module) for module in (vikram, betal, gopal)]
    for character in cast:
        export_fbx(character)
    studio(preview,cast)
    detail = surface_review(cast)
    wind, cloth = wind_review(cast[1])
    bake_and_verify(wind, cloth)
    configure_view(preview, camera=True)
    bpy.context.preferences.filepaths.save_version = 0
    result = bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Vikram_Betal_Cast.blend'),compress=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Could not save the character library')
    render_still(detail)
    render_still(preview)


if __name__ == '__main__':
    if '--wind-video' in sys.argv:
        render_wind_video()
    else:
        main()
