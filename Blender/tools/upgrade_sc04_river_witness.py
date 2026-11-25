"""Update the saved Chapter 1 lamp figure in place and retain its keyed rig."""

import json
from pathlib import Path
import sys

import bpy

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from character import Character
from river_witness_head import build_witness_head


def main():
    scene = next(scene for scene in bpy.data.scenes if scene.name.startswith('E01_SC04 | Performance'))
    bpy.context.window.scene = scene
    collection = scene.collection.children['CH_RiverFigure']
    previous = collection.objects.get('RiverFigure_Unidentified head without face')
    if previous is None:
        raise ValueError('Open an SC04 performance file with the original river witness head.')

    figure = Character.__new__(Character)
    figure.name = 'RiverFigure'
    figure.collection = collection
    figure.rig = collection.objects['RiverFigure_Rig']
    figure.scale = figure.rig.data.bones['head'].length / .301
    figure.parts = []
    build_witness_head(figure)
    timeline = TOOLS.parents[1] / 'Production/E01/E01_SC04_Animatic_Timeline.json'
    shots = json.loads(timeline.read_text(encoding='utf-8'))['shots']
    for part in figure.parts:
        for shot in shots:
            part.hide_render = shot['set'] != 'river'
            part.keyframe_insert('hide_render', frame=shot['start_frame'])
    bpy.data.objects.remove(previous, do_unlink=True)

    scene.frame_set(scene.frame_start)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)
    print(f'RIVER WITNESS HEAD SAVED: {len(figure.parts)} meshes on the original head bone', flush=True)


if __name__ == '__main__':
    main()
