"""Build SET_Town.blend (set 3): निचली बस्ती और अनाज मंडी - Halwai roof, front roof, the neighbour's
cattle place, the tall grain-market shed, the open refuge floor and modular houses.

Run from the repository root:
  blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_town_set.py

Same world map as SET_Palace and SET_Ghat (metres, +X east, +Y north, Z = 0 at the ghat quay). The ghat
terrain, low wall, gate and chowki are rebuilt in the group `Ghat context (from SET_Ghat)` so that the
market roof can be tested against the real gate. Link SET_Ghat.blend instead when merging.
"""

import json
import math
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ghat_kit as k
import ghat_story
import ghat_world
import town_art
import town_kit as K
import town_layout as T
import town_market
import town_world

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Blender/Sets/SET_Town.blend'
MANIFEST = ROOT / 'Blender/Sets/SET_Town_Manifest.json'


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'SET_Town'
    scene.unit_settings.system = 'METRIC'
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 1, 24
    scene.render.engine = 'CYCLES'
    scene.cycles.samples, scene.cycles.use_denoising = 64, True
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('Town | morning sky')
    if world.node_tree is None:  # use_nodes is deprecated in Blender 5.2 and removed in 6.0
        world.use_nodes = True
    background = world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.42, .56, .80, 1)
    background.inputs['Strength'].default_value = 1.0
    scene.world = world
    return scene


def ghat_context():
    """Ghat terrain, wall, gate and chowki at their real positions (no boat, no person, no night lights)."""
    g = ghat_world.materials()
    ghat_world.river_and_banks(g)
    ghat_world.steps_and_quay(g)
    ghat_world.low_wall(g)
    ghat_story.gate(g)
    ghat_story.chowki_and_lamp(g)
    water = g['water'].node_tree.nodes.get('Principled BSDF')
    water.inputs['Base Color'].default_value = (.10, .22, .26, 1)
    g['water'].diffuse_color = (.10, .22, .26, 1)
    for light in [o for o in bpy.data.objects if o.type == 'LIGHT']:
        bpy.data.objects.remove(light)
    group = bpy.data.collections.new('Ghat context (from SET_Ghat)')
    bpy.context.scene.collection.children.link(group)
    for col in [c for c in bpy.data.collections if c.name.startswith('Ghat |')]:
        bpy.context.scene.collection.children.unlink(col)
        group.children.link(col)


def lights():
    k.use(K.collection_named('Town | Lights'))
    sun = bpy.data.lights.new('Morning sun', 'SUN')
    sun.energy, sun.color, sun.angle = 3.2, (1.0, .88, .70), math.radians(2.5)
    obj = bpy.data.objects.new(sun.name, sun)
    k._current.objects.link(obj)
    obj.location, obj.rotation_euler = (-30, 120, 60), (math.radians(52), 0, math.radians(200))


def camera(name, lens, location, target=None, ortho=None):
    data = bpy.data.cameras.new(name)
    data.lens, data.clip_end, data.sensor_width = lens, 600, 36
    if ortho:
        data.type, data.ortho_scale = 'ORTHO', ortho
    obj = bpy.data.objects.new(name, data)
    k._current.objects.link(obj)
    obj.location = location
    if target:
        k.aim(obj, target)
    return obj


def cameras(scene):
    k.use(K.collection_named('Town | Cameras'))
    eye = T.HALWAI_EYE
    first = camera('CAM | Halwai roof eye to the ghat', 35, eye, target=(-21.0, -1.0, 2.0))
    camera('CAM | Halwai roof eye to the ghat (wide)', 20, eye, target=(-21.0, -1.0, 2.0))
    camera('CAM | Halwai west parapet to the cattle place', 28, T.WEST_STANCE, target=(*T.CATTLE['center'], .6))
    camera('CAM | Front roof to the Halwai roof', 35, T.FRONT_BOY, target=(-60.0, 78.5, T.HALWAI_ROOF_Z + 1.4))
    camera('CAM | Lane A looking west', 30, (-10.0, 72.5, 1.7), target=(-62.0, 72.5, 2.2))
    camera('CAM | Mandi shed from lane B', 24, (-14.0, 24.0, 2.2), target=(-38.0, 34.0, 5.0))
    camera('CAM | Refuge floor', 28, (4.0, 60.0, 5.0), target=(-10.0, 46.0, 0.0))
    camera('CAM | Cattle place', 30, (-66.0, 70.5, 2.4), target=(-71.0, 81.0, .8))
    camera('CAM | Top map (town, market, ghat)', 24, (-40, 40, 300), target=(-40, 40, 0), ortho=210)
    scene.camera = first


def write_manifest():
    data = dict(
        blend='Blender/Sets/SET_Town.blend', generator='Blender/tools/build_town_set.py', blender=bpy.app.version_string,
        units='metres; +X east, +Y north, +Z up; world Z 0 = ghat quay (same map as SET_Palace and SET_Ghat)',
        anchors=dict(halwai_roof_eye=list(T.HALWAI_EYE), mandi_ridge=list(T.RIDGE), gate=list(T.GATE),
                     front_roof_boy=list(T.FRONT_BOY), cattle_place=list(T.CATTLE['center']) + [0],
                     refuge_floor=list(T.REFUGE['center']) + [T.REFUGE['top']]),
        footprints={name: [round(v, 2) for v in rect] for name, rect in T.footprints().items()},
        cameras=sorted(o.name for o in bpy.data.objects if o.type == 'CAMERA'),
        collections={c.name: len(c.objects) for c in bpy.data.collections},
        mesh_objects=sum(1 for o in bpy.data.objects if o.type == 'MESH'),
        guesses=['All positions are guesses that satisfy the story: the roof-to-ghat sight line and the market roof covering the gate.',
                 'The ghat is rebuilt here only as context; SET_Ghat.blend remains the source for the gate and chowki.',
                 'House styles (mud, lime, ochre; thatch, tile, flat) follow an early-Indian village idiom and copy no real place.'])
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    scene = reset()
    m = K.materials()
    ghat_context()
    town_world.ground(m)
    for spec in T.HOUSES:
        gap = None
        if spec is T.HALWAI:  # the roof stair lands through the east parapet; gap measured from the house centre
            lo, hi = T.STAIR['parapet_gap']
            gap = ('E', lo - T.HALWAI['center'][1], hi - T.HALWAI['center'][1])
        K.house(spec, m, gap)
    K.modular_kit_row(m)
    town_world.halwai_extras(m)
    town_world.front_house_extras(m)
    town_market.mandi(m)
    town_market.cattle_place(m)
    town_world.refuge(m)
    town_world.trees(m)
    lights()
    town_art.sky(scene)
    cameras(scene)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
    write_manifest()
    print('Saved', OUT)


main()
