"""Build SET_Smashan.blend (set 4): श्मशान, बरगद और चबूतरा - horse tie, banyan with a low climbing
branch, hanging white cloth over two heels, entrance path, chabutra seat and a root seat for the last scene.

Run from the repository root:
  blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_smashan_set.py

The set uses a local map (metres, +X east, +Y north, origin on the entrance path) because the story gives no
route from the ghat or town.
"""

import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smashan_layout as L
import smashan_story
import smashan_world

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Blender/Sets/SET_Smashan.blend'
MANIFEST = ROOT / 'Blender/Sets/SET_Smashan_Manifest.json'


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'SET_Smashan'
    scene.unit_settings.system = 'METRIC'
    scene.frame_start, scene.frame_end, scene.render.fps = L.FRAME_START, L.FRAME_END, 24
    scene.render.engine = 'CYCLES'
    scene.cycles.samples, scene.cycles.use_denoising = 64, True
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('Smashan | dusk sky')
    if world.node_tree is None:  # use_nodes is deprecated in Blender 5.2 and removed in 6.0
        world.use_nodes = True
    background = world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.04, .06, .11, 1)
    background.inputs['Strength'].default_value = .5
    scene.world = world
    return scene


def write_manifest():
    data = dict(
        blend='Blender/Sets/SET_Smashan.blend', generator='Blender/tools/build_smashan_set.py',
        blender=bpy.app.version_string,
        units='metres; local map, +X east, +Y north, +Z up; origin on the entrance path',
        heights=dict(low_branch_seat_top_z=[round(L.low_top(s), 3) for s in (1.0, 2.0, 3.0)],
                     chabutra_top_z=L.CHABUTRA['height'],
                     root_seat_top_z=[round(L.root_top(s), 3) for s in L.ROOT_SEAT_S],
                     vikram_height=L.VIKRAM_HEIGHT, betal_height=L.BETAL_HEIGHT),
        anchors=dict(horse=list(L.HORSE_MARK), trunk=list(L.TRUNK), cloth=list(L.cloth_origin()),
                     heels=[list(h) for h in L.heels()], carry=list(L.VIKRAM_CARRY_MARK),
                     root_seat=list(L.root_seat_centre())),
        cloth_frames=L.CLOTH_FRAMES,
        cameras=sorted(o.name for o in bpy.data.objects if o.type == 'CAMERA'),
        collections={c.name: len(c.objects) for c in bpy.data.collections},
        mesh_objects=sum(1 for o in bpy.data.objects if o.type == 'MESH'),
        guesses=['All positions and sizes are guesses; the story fixes only the order of horse, banyan, cloth, heels, branch, root.',
                 'The set is on a local map and is not yet placed on the palace/ghat/town map.',
                 'Heels are simple stand-ins; swap in the Betal rig at MARK | Heels if needed.'])
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    scene = reset()
    m = smashan_world.materials()
    smashan_world.ground(m)
    smashan_world.boundary(m)
    smashan_world.horse_post(m)
    smashan_story.banyan(m)
    smashan_story.cloth_and_heels(m)
    smashan_story.chabutra(m)
    smashan_story.pyres(m)
    smashan_story.lights_and_cameras(scene)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
    write_manifest()
    print('Saved', OUT)


main()
