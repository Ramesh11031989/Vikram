"""Append the existing Chapter 1 sets into one editable sightline scene."""

import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cast import aim, turn


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Production/E01/Sightlines/E01_Ghat_Sightlines.blend'
MORNING, EVENING, ROOF, BOAT, TURNED = 1, 49, 97, 145, 238
SET_NAMES = ('SET_Palace.blend', 'SET_Ghat.blend', 'SET_Town.blend')
WINDOW_CAMERA = 'CAM | Chamber window — ghat steps (fixed)'
ROOF_CAMERA = 'CAM | Halwai roof eye to the ghat (wide)'
BOAT_CAMERA = 'CAM | Boat POV — Gopal seated eye'
SHOTS = ((MORNING, 'Palace window | Five dry steps', WINDOW_CAMERA),
         (EVENING, 'Palace window | Three dry steps', WINDOW_CAMERA),
         (ROOF, 'Halwai roof | Market hides the gate', ROOF_CAMERA),
         (BOAT, 'Gopal seated eye | Lamp and red cloth', BOAT_CAMERA),
         (TURNED, 'Gopal seated eye | Boat turned downstream', BOAT_CAMERA))


def append_collections(path, selection, parent):
    with bpy.data.libraries.load(str(path), link=False) as (available, chosen):
        chosen.collections = [name for name in available.collections if selection(name)]
        if not chosen.collections:
            raise ValueError(f'No assembly collections found in {path}')
    for collection in chosen.collections:
        parent.children.link(collection)
    return chosen.collections


def assembly_collection(scene, name):
    collection = bpy.data.collections.new(name)
    scene.collection.children.link(collection)
    return collection


def action_curves(owner):
    animation = owner.animation_data
    if animation is None or animation.action is None or animation.action_slot is None:
        return
    for layer in animation.action.layers:
        for strip in layer.strips:
            bag = strip.channelbag(animation.action_slot)
            if bag is not None:
                yield from bag.fcurves


def retime(owner, convert, constant=False):
    for curve in action_curves(owner):
        for key in curve.keyframe_points:
            shift = convert(key.co.x) - key.co.x
            key.co.x += shift
            key.handle_left.x += shift
            key.handle_right.x += shift
            if constant:
                key.interpolation = 'CONSTANT'
        curve.update()


def light_or_color_keys(owner, path, first, last):
    setattr(owner, path, first)
    owner.keyframe_insert(path, frame=MORNING)
    setattr(owner, path, last)
    owner.keyframe_insert(path, frame=BOAT)


def set_key_constant(owner, frame):
    for curve in action_curves(owner):
        for key in curve.keyframe_points:
            if abs(key.co.x - frame) < .001:
                key.interpolation = 'CONSTANT'


def configure_palace(scene):
    # The palace presets originally occupy frames 1 and 2. Hold both as shot states.
    owners = [scene, scene.world.node_tree, *bpy.data.objects, *bpy.data.lights]
    owners.extend(material.node_tree for material in bpy.data.materials if material.node_tree)
    for owner in owners:
        retime(owner, lambda frame: MORNING if frame == 1 else EVENING if frame == 2 else frame, constant=True)
    placeholder = next(c for c in bpy.data.collections if c.name.startswith('PLACEHOLDER | Ghat'))
    wet_stone = next(m for m in bpy.data.materials if m.name.startswith('Ghat | river stone, wet line'))
    silty_water = next(m for m in bpy.data.materials if m.name.startswith('River | silty flood water'))
    terrain = placeholder.objects['PLACEHOLDER | Terrain and riverbed']
    terrain.name = 'Palace | Distant terrain below the combined set'
    backdrop = assembly_collection(scene, 'Sightlines | Distant terrain')
    backdrop.objects.link(terrain)
    for vertex in terrain.data.vertices:
        if -92 <= vertex.co.x <= 92 and -72 <= vertex.co.y <= 96:
            vertex.co.z = min(-4.10, vertex.co.z)
    terrain.data.update()
    bpy.data.collections.remove(placeholder)
    scene.frame_set(EVENING)
    return wet_stone, silty_water


def configure_river(wet_stone, silty_water):
    for index in range(1, 9):
        bpy.data.objects[f'Ghat step {index}'].data.materials[0] = wet_stone
    water = bpy.data.objects['River water surface']
    original_level = water.data.vertices[0].co.z
    water.data.transform(Matrix.Translation((0, 0, -original_level)))
    water.data.materials[0] = silty_water
    route = next(o for o in bpy.data.objects if o.name.startswith('Boat route ('))
    route.hide_render = True
    route.hide_viewport = True
    boat = bpy.data.objects['Boat | root (route + yaw)']
    for obj in (water, boat):
        for frame, level in ((MORNING, -2.2), (EVENING, -1.4)):
            obj.location.z = level
            obj.keyframe_insert('location', index=2, frame=frame)
            set_key_constant(obj, frame)
    water['Water levels (m)'] = 'Window morning −2.2; window later and testimony −1.4.'


def marker(collection, name, world_position, yaw=None):
    obj = bpy.data.objects.new(name, None)
    collection.objects.link(obj)
    obj.location = world_position
    obj.empty_display_size = .15
    if yaw is not None:
        obj.rotation_euler.z = yaw
    return obj


def stage_lamp(ghat, cloth_sample):
    chowki = next(c for c in ghat.children if c.name.startswith('Ghat | Chowki'))
    bowl = chowki.objects['Clay lamp bowl']
    ledge = chowki.objects['Lamp ledge']
    spot = next(obj for obj in chowki.objects if obj.name.startswith('Lamp spot'))
    # The rim of the old shelf blocked the wick from the low boat camera and cast a shadow on the cloth.
    offset = Vector((.13, .17, .14))
    for obj in (bowl, chowki.objects['Lamp flame'], spot):
        obj.location += offset
    bpy.context.view_layer.update()
    seat = max((ledge.matrix_world @ Vector(corner)).z for corner in ledge.bound_box) - .002
    top = min((bowl.matrix_world @ Vector(corner)).z for corner in bowl.bound_box) + .011
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=.069, radius2=.048, depth=top - seat,
                                  location=(bowl.location.x, bowl.location.y, (seat + top) / 2))
    stand = bpy.context.object
    stand.name = 'Lamp | Low clay stand on the ledge'
    chowki.objects.link(stand)
    for collection in list(stand.users_collection):
        if collection != chowki:
            collection.objects.unlink(stand)
    stand.data.materials.append(bowl.data.materials[0])
    aim(spot, cloth_sample)
    return spot


def place_unidentified(scene, ghat, source):
    previous = next(c for c in ghat.children if c.name.startswith('Ghat | Unidentified person'))
    source_mark = next(o for o in previous.objects if o.name.startswith('MARK | Person'))
    position, yaw = source_mark.location.copy(), source_mark.rotation_euler.z
    bpy.data.collections.remove(previous)
    figure, = append_collections(source, lambda name: name == 'CH_AnonymousRedCloth', ghat)
    rig = figure.objects['AnonymousRedCloth_Rig']
    rig.location, rig.rotation_euler.z = position, yaw + math.pi
    rig['Shot use'] = 'Back and shoulder only. The character is anonymous and has no face rig.'
    for side, sign in (('L', 1), ('R', -1)):
        turn(rig, f'upper_arm.{side}', (0, 1, 0), sign * 76)
        turn(rig, f'forearm.{side}', (0, 0, 1), sign * -8)
    turn(rig, 'head', (0, 0, 1), -28)
    turn(rig, 'neck', (0, 0, 1), -10)
    turn(rig, 'chest', (0, 0, 1), -6)
    for part in rig.children:
        light_or_color_keys(part, 'hide_render', True, False)
        set_key_constant(part, MORNING)
    bpy.context.view_layer.update()

    proof = assembly_collection(scene, 'Sightlines | Proof marks')
    marker(proof, 'MARK | Red cloth figure root', position, rig.rotation_euler.z)
    # Sample the actual skinned back drape and keep the diagnostic point just off its surface.
    cloth = figure.objects['AnonymousRedCloth_Red cloth over shoulders']
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = cloth.evaluated_get(graph)
    desired = rig.matrix_world @ Vector((.014, .148, 1.21))
    sample = min((evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices),
                 key=lambda point: (desired - point).length_squared)
    back = rig.matrix_world.to_3x3() @ Vector((0, 1, 0))
    marker(proof, 'MARK | Red cloth witness sample', sample + back.normalized() * .012)
    return stage_lamp(ghat, sample)


def configure_lighting(scene, ghat, spot):
    tree = scene.world.node_tree
    background = next(node for node in tree.nodes if node.type == 'BACKGROUND')
    original_sky = background.inputs['Color'].links[0].from_socket
    mix = tree.nodes.new('ShaderNodeMixRGB')
    mix.label = 'Palace sky / Ghat night sky'
    mix.location = (background.location.x - 210, background.location.y - 140)
    mix.inputs[2].default_value = (.035, .055, .10, 1)
    tree.links.new(original_sky, mix.inputs[1])
    tree.links.new(mix.outputs[0], background.inputs['Color'])
    light_or_color_keys(mix.inputs[0], 'default_value', 0, 1)
    background.inputs['Strength'].default_value = .70
    background.inputs['Strength'].keyframe_insert('default_value', frame=BOAT)
    set_key_constant(tree, MORNING)
    set_key_constant(tree, EVENING)
    for light in bpy.data.lights:
        if light.type == 'SUN':
            light.energy = 0
            light.keyframe_insert('energy', frame=BOAT)
            set_key_constant(light, EVENING)
    ghat_lights = next(c for c in ghat.children if c.name == 'Ghat | Lights')
    bounce = ghat_lights.objects['Quay faint moon bounce']
    bounce.location = (-11.3, -5.4, 6.4)
    aim(bounce, (-12.1, -.25, .0))
    bounce.data.energy, bounce.data.size, bounce.data.spread = 95, 5.5, math.radians(64)
    spot.data.energy = 62
    for obj in (*ghat_lights.objects, spot):
        light_or_color_keys(obj.data, 'energy', 0, obj.data.energy)
        set_key_constant(obj.data, MORNING)
    scene.view_settings.exposure = 0
    scene.keyframe_insert('view_settings.exposure', frame=BOAT)
    set_key_constant(scene, EVENING)


def configure_review(scene):
    cameras = {name: bpy.data.objects[name] for _, _, name in SHOTS}
    for obj in list(scene.objects):
        if obj.type == 'CAMERA' and obj.name not in cameras:
            bpy.data.objects.remove(obj, do_unlink=True)
    cameras[WINDOW_CAMERA].data.lens = 67
    boat_camera = cameras[BOAT_CAMERA]
    boat_camera.data.lens = 60
    boat_camera.keyframe_insert('rotation_euler', index=0, frame=205)
    boat_camera.rotation_euler.x = math.radians(87)
    boat_camera.keyframe_insert('rotation_euler', index=0, frame=TURNED)
    scene.timeline_markers.clear()
    for frame, label, name in SHOTS:
        scene.timeline_markers.new(label, frame=frame).camera = cameras[name]
    scene.timeline_markers.new('Boat begins yawing downstream', frame=180)
    scene.timeline_markers.new('Grille still down at end of testimony', frame=293)
    scene.timeline_markers.new('Grille reaches raised position', frame=354)
    scene.frame_start, scene.frame_end, scene.render.fps = MORNING, 384, 24
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.adaptive_threshold = .055
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1440, 810
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = '//Renders/'
    scene.camera = cameras[WINDOW_CAMERA]
    scene.frame_set(MORNING)
    bpy.context.preferences.filepaths.save_version = 0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_perspective = 'CAMERA'
                area.spaces.active.overlay.show_overlays = False
                area.spaces.active.shading.color_type = 'MATERIAL'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sets', type=Path, default=ROOT / 'Blender/Sets')
    parser.add_argument('--figure', type=Path, default=ROOT / 'Blender/Characters/Anonymous_Red_Cloth/Anonymous_Red_Cloth.blend')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    palace, ghat_source, town_source = (args.sets.resolve() / name for name in SET_NAMES)
    figure_source = args.figure.resolve()
    for path in (palace, ghat_source, town_source, figure_source):
        if not path.is_file():
            raise FileNotFoundError(path)

    bpy.ops.wm.open_mainfile(filepath=str(palace))
    scene = bpy.context.scene
    scene.name = 'E01 Ghat Sightlines'
    wet_stone, silty_water = configure_palace(scene)
    ghat = assembly_collection(scene, 'SET_Ghat | River, gate and boat')
    town = assembly_collection(scene, 'SET_Town | Roof, market and settlement')
    append_collections(ghat_source, lambda name: name.startswith('Ghat | '), ghat)
    append_collections(town_source, lambda name: name.startswith('Town | ') and name != 'Town | Lights', town)
    for obj in ghat.all_objects:
        retime(obj, lambda frame: frame + BOAT - 1)
    configure_river(wet_stone, silty_water)
    scene.frame_set(BOAT)
    spot = place_unidentified(scene, ghat, figure_source)
    configure_lighting(scene, ghat, spot)
    configure_review(scene)
    scene['Source sets'] = 'Palace, Ghat, Town and Anonymous Red Cloth, appended as local editable data.'
    scene['Map'] = 'Metres. +X east, +Y north, Z 0 at the ghat quay.'
    scene['Evidence'] = 'One fixed window camera. Market roof occludes gate. Boat sees back and cloth only.'
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    bpy.ops.file.pack_all()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
    print(f'Assembled {len(scene.objects)} objects and {len(SHOTS)} review frames in {output}', flush=True)


if __name__ == '__main__':
    main()
