"""Build SET_Ghat.blend: नदी, घाट और फाटक (river bend, stone steps, lifting gate, chowki,
lamp place, low riverside wall and the boat route).

Run from the repository root:
  blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_ghat_set.py

Same world map as the palace set: metres, +X east, +Y north, Z = 0 at the ghat's top quay.
"""

import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ghat_boat
import ghat_layout as L
import ghat_story
import ghat_world

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Blender/Sets/SET_Ghat.blend'
MANIFEST = ROOT / 'Blender/Sets/SET_Ghat_Manifest.json'


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'SET_Ghat'
    scene.unit_settings.system = 'METRIC'
    scene.frame_start, scene.frame_end, scene.render.fps = L.FRAME_START, L.FRAME_END, 24
    scene.render.engine = 'CYCLES'
    scene.cycles.samples, scene.cycles.use_denoising = 96, True
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('Ghat | night sky')
    if world.node_tree is None:
        world.use_nodes = True
    background = world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.035, .055, .10, 1)
    background.inputs['Strength'].default_value = .35
    scene.world = world
    return scene


def write_manifest():
    data = dict(
        blend='Blender/Sets/SET_Ghat.blend', generator='Blender/tools/build_ghat_set.py', blender=bpy.app.version_string,
        units='metres; +X east, +Y north, +Z up; world Z 0 = ghat quay (same map as SET_Palace)',
        water_z=L.WATER_Z, dry_treads=L.dry_treads(), bank_y=L.BANK_Y,
        anchors=dict(gate=[L.GATE_X, L.GATE_Y, 0], lamp=list(L.LAMP), person=list(L.PERSON)),
        boat_route=[list(p) for p in L.BOAT_ROUTE],
        frames=dict(start=L.FRAME_START, end=L.FRAME_END, yaw_turn=list(L.YAW_TURN_FRAMES),
                    gate_raise=list(L.GATE_RAISE_FRAMES)),
        cameras=sorted(o.name for o in bpy.data.objects if o.type == 'CAMERA'),
        collections={c.name: len(c.objects) for c in bpy.data.collections},
        mesh_objects=sum(1 for o in bpy.data.objects if o.type == 'MESH'),
        guesses=['Gate, chowki, lamp and person positions are guesses from the palace map_anchors; the story fixes only their order.',
                 'The person is a back-only unidentified stand-in; swap in the Anonymous_Red_Cloth rig at MARK | Person.'])
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    scene = reset()
    m = ghat_world.materials()
    ghat_world.river_and_banks(m)
    ghat_world.steps_and_quay(m)
    ghat_world.low_wall(m)
    ghat_story.gate(m)
    ghat_story.chowki_and_lamp(m)
    ghat_story.person(m)
    rock = ghat_boat.boat(m)
    ghat_boat.lights()
    ghat_boat.cameras(scene, rock)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
    write_manifest()
    print('Saved', OUT)


main()
