"""Build the chapter cast, an editable character library and its FBX handoff."""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character import Character
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
    for side, sign in (('L',1),('R',-1)):
        turn(rig, f'upper_arm.{side}', (0,1,0), sign*(77 if character.name=='Vikram' else 75))
        turn(rig,f'forearm.{side}', (0,0,1), sign*(-9 if character.name=='Gopal' else -5))
        for digit in range(1,5):
            turn(rig,f'finger_{digit:02d}.{side}', (0,1,0), sign*(12+digit*2))
    turn(rig,'head',(0,0,1),-yaw*.35)
    turn(rig,'chest',(0,1,0),-2 if character.name=='Betal' else 1)
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


def studio(scene, cast):
    bpy.context.window.scene = scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.name = 'Cast Preview'
    scene.render.fps = 24
    scene.unit_settings.system = 'METRIC'
    scene.world = bpy.data.worlds.new('Studio Ambient')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.26,.31,.37,1)
    background.inputs['Strength'].default_value = .26
    scene.view_settings.view_transform = 'AgX'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1500
    scene.render.resolution_y = 1120
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'

    baked_clay = studio_material('Backdrop • River clay',(.16,.112,.075))
    platform = studio_material('Pedestal • Warm sandstone',(.33,.253,.17))
    lettering = studio_material('Labels • Charcoal',(.055,.027,.016))
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.25))
    floor = prop_material(bpy.context.object, baked_clay)
    floor.name = 'Studio floor'

    cam_data = bpy.data.cameras.new('Cast camera')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 3.45
    camera = bpy.data.objects.new('Cast camera',cam_data)
    scene.collection.objects.link(camera)
    camera.location = (0,-7,2.35)
    aim(camera,(0,0,.95))
    scene.camera = camera
    light(scene,'Soft daylight key',(-3,-4,6), (0,0,1), (1,.86,.68), 510,4.0)
    light(scene,'Cool fill',(3,-3,3),(0,0,1), (.61,.78,1), 280,3.3)
    light(scene,'Warm rim',(1.2,3,5),(0,0,1), (1,.72,.47), 620,3.0)

    for character, x, yaw, role in zip(cast,(-1.04,0,1.04),(10,-7,-12),('THE KING','THE CLERK','THE BOATMAN')):
        showcase_character(scene,character,x,yaw)
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=.449, depth=.21, location=(x,0,-.109))
        pedestal = prop_material(bpy.context.object,platform)
        pedestal.name = f'{character.name} • Sandstone plinth'
        bevel = pedestal.modifiers.new('Stone bevel','BEVEL')
        bevel.width = .026
        bevel.segments = 4
        pedestal.modifiers.new('Surface normals','WEIGHTED_NORMAL')
        label(scene, f'{character.name} Label', character.name.upper(), x, -.117, .086, lettering, camera, -.492)
        label(scene, f'{character.name} Role', role, x, -.181, .040, lettering, camera, -.501)
    bpy.ops.object.select_all(action='DESELECT')
    configure_view(scene, camera=True)


def main():
    (ROOT/'Exports').mkdir(exist_ok=True)
    (ROOT/'Previews').mkdir(exist_ok=True)
    preview = bpy.context.scene
    cast = [make_character(module) for module in (vikram, betal, gopal)]
    for character in cast:
        export_fbx(character)
    studio(preview,cast)
    bpy.context.preferences.filepaths.save_version = 0
    preview.render.filepath = '//Previews/Cast_Lineup.png'
    result = bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Vikram_Betal_Cast.blend'),compress=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Could not save the character library')
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
