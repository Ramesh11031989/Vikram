"""Build SET_Sharan.blend (set 5): शरण की ढलान और बेताल की झोपड़ी - the high ground behind the cremation
ground where families and boatmen sat in arrival order, the footpath up the slope and the outside of
Betal's hut.

Run from the repository root:
  blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_sharan_set.py

The set uses a local map (metres, +X east, +Y north/uphill, origin at the foot of the path) because the
story gives no route from the ghat or town.
"""

import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sharan_detail
import sharan_hut
import sharan_layout as L
import sharan_seating
import sharan_view
import sharan_world

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Blender/Sets/SET_Sharan.blend'
MANIFEST = ROOT / 'Blender/Sets/SET_Sharan_Manifest.json'


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'SET_Sharan'
    scene.unit_settings.system = 'METRIC'
    scene.frame_start, scene.frame_end, scene.render.fps = L.FRAME_START, L.FRAME_END, 24
    scene.render.engine = 'CYCLES'
    scene.cycles.samples, scene.cycles.use_denoising = 64, True
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('Sharan | dusk sky')
    if world.node_tree is None:  # use_nodes is deprecated in Blender 5.2 and removed in 6.0
        world.use_nodes = True
    background = world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.04, .06, .11, 1)
    background.inputs['Strength'].default_value = .5
    scene.world = world
    return scene


def write_manifest():
    seats = L.seats()
    data = dict(
        blend='Blender/Sets/SET_Sharan.blend', generator='Blender/tools/build_sharan_set.py',
        blender=bpy.app.version_string,
        units='metres; local map, +X east, +Y north (uphill), +Z up; origin at the foot of the path',
        heights=dict(terrace_z=L.base_z(15.0), platform_z=L.PLATFORM_Z, hut_floor_z=round(L.hut_floor_z(), 3),
                     hut_eave_z=round(L.eave_z(), 3), hut_ridge_z=round(L.ridge_z(), 3),
                     vikram_height=L.VIKRAM_HEIGHT, betal_height=L.BETAL_HEIGHT),
        path=dict(width=L.path_width(), max_grade_deg=round(L.max_path_grade_deg(), 2), y_range=list(L.PATH_Y)),
        seating=dict(count=len(seats), gopal_seat=L.GOPAL_SEAT, hearing_radius=L.HEARING_M,
                     seats=[dict(n=s['n'], x=round(s['x'], 3), y=round(s['y'], 3), z=round(s['z'], 3)) for s in seats],
                     mausi=[round(v, 3) for v in (L.mausi()['x'], L.mausi()['y'], L.mausi()['z'])]),
        anchors=dict(hut_door=list(L.door_centre()), veranda=list(L.veranda_mark()),
                     board=[round(v, 3) for v in L.board_marks()['betal']], nandu=list(L.nandu_mark())),
        cameras=sorted(o.name for o in bpy.data.objects if o.type == 'CAMERA'),
        collections={c.name: len(c.objects) for c in bpy.data.collections},
        mesh_objects=sum(1 for o in bpy.data.objects if o.type == 'MESH'),
        guesses=['All positions and sizes are guesses; the story fixes only the slope, the arrival-order list, '
                 "Gopal's third place and the hut at the top of the slope.",
                 'The set is on a local map and is not yet placed on the palace/ghat/town map.',
                 'Only the outside of the hut is modelled; the inside is a dark box with a charpai.',
                 'People are not included; SEAT, MARK and Mausi empties give their places.'])
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    scene = reset()
    m = sharan_detail.extra_materials(sharan_world.materials())
    sharan_world.terrain(m)
    sharan_world.path(m)
    sharan_world.cremation_edge(m)
    sharan_seating.seating(m)
    sharan_seating.trees(m)
    sharan_hut.hut(m)
    sharan_hut.yard(m)
    sharan_view.lights_and_cameras(scene)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
    write_manifest()
    print('Saved', OUT)


main()
